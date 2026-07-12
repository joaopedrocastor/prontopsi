"""Integracao opcional com a Agenda Google (Google Calendar).

Empurra os agendamentos do ProntoPsi para um calendario Google, para
sincronizar a organizacao. Tudo e "best-effort": se as bibliotecas nao
estiverem instaladas, ou a conta nao estiver conectada, o agendamento local
continua funcionando normalmente.

Fluxo OAuth (app desktop instalado):
  1. A psicologa cria um projeto no Google Cloud, ativa a API do Calendar e
     cria uma credencial OAuth do tipo "Aplicativo para computador".
  2. Informa client_id e client_secret nas Configuracoes do ProntoPsi.
  3. Clica em "Conectar" -> abre o navegador para autorizar -> o token fica
     salvo em google_token.json no diretorio de dados.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_data_dir
from ..models import Appointment, Settings
from ..utils import new_uuid, now_iso
from .settings_service import get_settings

logger = logging.getLogger("anamnese")

# calendar.events: criar/editar eventos. calendar.readonly: listar TODOS os
# calendários e ler eventos deles. drive.file: só arquivos que o app cria.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.file",
]
DRIVE_FOLDER_NAME = "ProntoPsi - Fichas"

try:  # bibliotecas opcionais
    import io as _io

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    GOOGLE_AVAILABLE = True
except Exception:  # pragma: no cover - ambiente sem as libs
    GOOGLE_AVAILABLE = False


def _token_path() -> Path:
    return get_data_dir() / "google_token.json"


def is_configured(settings: Settings) -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def is_connected() -> bool:
    return GOOGLE_AVAILABLE and _token_path().exists()


def status(db: Session) -> dict:
    settings = get_settings(db)
    return {
        "available": GOOGLE_AVAILABLE,
        "configured": is_configured(settings),
        "connected": is_connected(),
        "calendar_id": settings.google_calendar_id or "primary",
        "timezone": settings.google_timezone or "America/Sao_Paulo",
    }


def _client_config(settings: Settings) -> dict:
    return {
        "installed": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def connect(db: Session) -> dict:
    """Abre o navegador para autorizar e salva o token. Bloqueia ate concluir."""
    if not GOOGLE_AVAILABLE:
        raise ValueError("Bibliotecas do Google não instaladas nesta versão.")
    settings = get_settings(db)
    if not is_configured(settings):
        raise ValueError("Informe o client_id e o client_secret do Google primeiro.")
    flow = InstalledAppFlow.from_client_config(_client_config(settings), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", authorization_prompt_message="")
    _token_path().write_text(creds.to_json(), encoding="utf-8")
    return {"connected": True}


def disconnect() -> None:
    try:
        _token_path().unlink(missing_ok=True)
    except OSError:
        pass


def _credentials(settings: Settings):
    if not is_connected():
        return None
    creds = Credentials.from_authorized_user_file(str(_token_path()), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _token_path().write_text(creds.to_json(), encoding="utf-8")
    return creds


def _service(settings: Settings):
    creds = _credentials(settings)
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _event_body(appt: Appointment, tz: str) -> dict:
    resumo = appt.title or (appt.patient.name if appt.patient else "Consulta")
    return {
        "summary": resumo,
        "description": (appt.notes or "") + ("\n\nModalidade: " + appt.modality if appt.modality else ""),
        "start": {"dateTime": appt.start_at + ":00", "timeZone": tz},
        "end": {"dateTime": appt.end_at + ":00", "timeZone": tz},
    }


def sync_appointment(db: Session, appt: Appointment) -> None:
    """Cria/atualiza o evento no Google. Nunca levanta erro para o chamador."""
    try:
        settings = get_settings(db)
        service = _service(settings)
        if not service:
            return
        cal = settings.google_calendar_id or "primary"
        body = _event_body(appt, settings.google_timezone or "America/Sao_Paulo")
        if appt.google_event_id:
            service.events().update(calendarId=cal, eventId=appt.google_event_id, body=body).execute()
        else:
            ev = service.events().insert(calendarId=cal, body=body).execute()
            appt.google_event_id = ev.get("id")
            db.commit()
    except Exception as exc:  # best-effort
        logger.warning("Falha ao sincronizar com Google Agenda: %s", exc)


def delete_event(db: Session, google_event_id: str | None) -> None:
    if not google_event_id:
        return
    try:
        settings = get_settings(db)
        service = _service(settings)
        if not service:
            return
        cal = settings.google_calendar_id or "primary"
        service.events().delete(calendarId=cal, eventId=google_event_id).execute()
    except Exception as exc:  # best-effort
        logger.warning("Falha ao remover evento do Google: %s", exc)


def _wallclock(dt_str: str) -> str | None:
    """RFC3339 do Google -> 'YYYY-MM-DDTHH:MM' (horário local do evento).

    O Google já formata a data no fuso do evento (ex.: ...T10:00:00-03:00),
    então os 16 primeiros caracteres são exatamente o horário de parede.
    """
    if not dt_str or "T" not in dt_str:
        return None  # evento de dia inteiro (só 'date') — ignorado
    return dt_str[:16]


def _list_calendar_ids(service, settings) -> list[str]:
    """IDs dos calendários a sincronizar.

    Se a usuária fixou um calendário nas configurações (diferente de 'primary'),
    usa só ele. Caso contrário, lista TODOS os calendários da conta (assim
    eventos criados em qualquer 'agenda' do Google são trazidos, não só o
    principal). Se não conseguir listar, cai no 'primary'.
    """
    configured = (settings.google_calendar_id or "").strip()
    if configured and configured.lower() != "primary":
        return [configured]
    try:
        ids, page = [], None
        while True:
            resp = service.calendarList().list(pageToken=page, maxResults=250).execute()
            ids += [it["id"] for it in resp.get("items", [])]
            page = resp.get("nextPageToken")
            if not page:
                break
        return ids or ["primary"]
    except Exception as exc:
        logger.info("Não foi possível listar calendários (%s); usando o principal.", exc)
        return ["primary"]


def pull_events(db: Session, days_back: int = 30, days_forward: int = 365) -> dict:
    """Traz os eventos do Google para a agenda do app (Google -> app).

    Lê TODOS os calendários da conta (ou o fixado nas configurações). Casa pelo
    google_event_id (não duplica): cria os novos e atualiza os existentes. Por
    segurança, NÃO apaga agendamentos do app. Eventos de dia inteiro e
    cancelados são ignorados.
    """
    settings = get_settings(db)
    if not is_configured(settings):
        raise ValueError("Configure o Google primeiro.")
    service = _service(settings)
    if not service:
        raise ValueError("Conecte a conta do Google (Conectar) antes de sincronizar.")

    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days_back)).isoformat()
    time_max = (now + timedelta(days=days_forward)).isoformat()

    stats = {"created": 0, "updated": 0, "skipped": 0, "calendars": 0}
    for cal in _list_calendar_ids(service, settings):
        stats["calendars"] += 1
        page_token = None
        while True:
            try:
                resp = service.events().list(
                    calendarId=cal, timeMin=time_min, timeMax=time_max,
                    singleEvents=True, orderBy="startTime", maxResults=250,
                    pageToken=page_token,
                ).execute()
            except Exception as exc:  # um calendário sem acesso não derruba os outros
                logger.info("Falha ao ler calendário %s (%s).", cal, exc)
                break
            for ev in resp.get("items", []):
                if ev.get("status") == "cancelled":
                    stats["skipped"] += 1
                    continue
                start = _wallclock((ev.get("start") or {}).get("dateTime"))
                end = _wallclock((ev.get("end") or {}).get("dateTime")) or start
                if not start:
                    stats["skipped"] += 1  # dia inteiro / sem horário
                    continue
                gid = ev.get("id")
                title = ev.get("summary") or "Evento (Google)"
                notes = ev.get("description") or None

                existing = db.scalar(select(Appointment).where(Appointment.google_event_id == gid))
                if existing:
                    existing.title = title
                    existing.start_at = start
                    existing.end_at = end
                    if notes is not None:
                        existing.notes = notes
                    stats["updated"] += 1
                else:
                    db.add(Appointment(
                        id=new_uuid(), patient_id=None, title=title,
                        start_at=start, end_at=end, status="agendada",
                        notes=notes, google_event_id=gid,
                        created_at=now_iso(), updated_at=now_iso(),
                    ))
                    stats["created"] += 1
            db.commit()
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    return stats


# ---------------- Google Drive (salvar PDFs das fichas) ----------------
def _drive_service(settings: Settings):
    creds = _credentials(settings)
    if not creds:
        return None
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _ensure_drive_folder(service) -> str:
    """Acha (ou cria) a pasta 'ProntoPsi - Fichas' no Drive e devolve o id."""
    q = (f"mimeType='application/vnd.google-apps.folder' and "
         f"name='{DRIVE_FOLDER_NAME}' and trashed=false")
    res = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": DRIVE_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    return service.files().create(body=meta, fields="id").execute()["id"]


def upload_pdf(db: Session, filename: str, pdf_bytes: bytes,
               existing_file_id: str | None = None) -> dict:
    """Sobe (ou atualiza) um PDF na pasta do ProntoPsi no Drive.

    Retorna {id, link}. Levanta ValueError com mensagem amigável em caso de
    problema (ex.: precisa reconectar para autorizar o Drive).
    """
    if not GOOGLE_AVAILABLE:
        raise ValueError("Integração Google não disponível nesta versão.")
    if not is_connected():
        raise ValueError("Conecte o Google primeiro (Configuração).")
    settings = get_settings(db)
    service = _drive_service(settings)
    if not service:
        raise ValueError("Conecte o Google primeiro (Configuração).")

    def _media():
        return MediaIoBaseUpload(_io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False)

    def _create():
        folder_id = _ensure_drive_folder(service)
        body = {"name": filename, "parents": [folder_id]}
        return service.files().create(body=body, media_body=_media(),
                                      fields="id,webViewLink").execute()

    try:
        if existing_file_id:
            try:
                f = service.files().update(fileId=existing_file_id, media_body=_media(),
                                           fields="id,webViewLink").execute()
            except Exception:  # arquivo apagado no Drive -> cria de novo
                f = _create()
        else:
            f = _create()
        return {"id": f.get("id"), "link": f.get("webViewLink")}
    except Exception as exc:
        raise ValueError(
            "Falha ao enviar para o Drive. Talvez seja preciso clicar em "
            f"Conectar de novo para autorizar o Google Drive. ({exc})"
        ) from exc
