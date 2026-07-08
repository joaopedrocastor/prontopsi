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
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import get_data_dir
from ..models import Appointment, Settings
from .settings_service import get_settings

logger = logging.getLogger("anamnese")

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

try:  # bibliotecas opcionais
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
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
