"""Regras de negocio de Configuracoes / identidade visual.

Sem nenhuma dependencia de FastAPI ou da interface (camada de servico).
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import FRONTEND_DIR, get_assets_dir, get_data_dir
from ..models import Settings

_ALLOWED_LOGO_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def get_settings(db: Session) -> Settings:
    """Retorna a linha unica de configuracao, criando-a se ainda nao existir."""
    settings = db.scalar(select(Settings))
    if settings is None:
        settings = Settings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, *, professional_name: str, professional_title: str,
                    crp: str, logo_includes_info: bool = False) -> Settings:
    settings = get_settings(db)
    settings.professional_name = professional_name.strip()
    settings.professional_title = (professional_title or "Psicóloga").strip()
    settings.crp = crp.strip()
    settings.logo_includes_info = bool(logo_includes_info)
    db.commit()
    db.refresh(settings)
    return settings


# Consultórios sugeridos enquanto a lista nunca foi salva (offices = NULL).
# Depois que a usuária salva "Dados do recibo", vale só o que ela cadastrou
# (inclusive lista vazia).
DEFAULT_OFFICES = [
    {"city": "Ponte Nova - MG",
     "address": "Travessa Mário Bonfati, 01, 407 - Centro, Ponte Nova - MG",
     "phone": "(31) 98974-0737"},
    {"city": "Barra Longa - MG",
     "address": "Rua Monsenhor Hort, 04, Loja 01 - Centro - Barra Longa- MG",
     "phone": "(31) 98974-0737"},
]


def get_offices(settings: Settings) -> list[dict]:
    """Consultórios cadastrados (lista de {city, address, phone})."""
    if settings.offices is None:
        return [dict(o) for o in DEFAULT_OFFICES]
    try:
        data = json.loads(settings.offices or "[]")
    except (ValueError, TypeError):
        return []
    out = []
    for o in data if isinstance(data, list) else []:
        if isinstance(o, dict) and (o.get("city") or "").strip():
            out.append({"city": (o.get("city") or "").strip(),
                        "address": (o.get("address") or "").strip(),
                        "phone": (o.get("phone") or "").strip()})
    return out


def find_office(settings: Settings, city: str) -> dict | None:
    """Consultório pela cidade (sem diferenciar maiúsculas/acentos de espaço)."""
    alvo = (city or "").strip().lower()
    for o in get_offices(settings):
        if o["city"].lower() == alvo:
            return o
    return None


def update_receipt_settings(db: Session, *, legal_name: str | None, cpf: str | None,
                            offices: list[dict], receipt_next: int | None) -> Settings:
    settings = get_settings(db)
    settings.legal_name = (legal_name or "").strip() or None
    settings.cpf = (cpf or "").strip() or None
    limpos = [o for o in offices if (o.get("city") or "").strip()]
    settings.offices = json.dumps(limpos, ensure_ascii=False)
    if receipt_next and receipt_next > 0:
        settings.receipt_next = int(receipt_next)
    db.commit()
    db.refresh(settings)
    return settings


def register_receipt_number(db: Session, number: int) -> None:
    """Após emitir o recibo nº N, o próximo sugerido passa a ser N+1 (nunca volta)."""
    settings = get_settings(db)
    if number and number >= (settings.receipt_next or 1):
        settings.receipt_next = number + 1
        db.commit()


def save_logo(db: Session, *, filename: str, content: bytes) -> Settings:
    """Salva a logo em disco (pasta de assets) e guarda o caminho RELATIVO."""
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_LOGO_EXT:
        raise ValueError("Formato de imagem não suportado. Use PNG ou JPG.")

    settings = get_settings(db)
    _remove_old_logo(settings)

    dest_name = f"logo{ext}"
    dest = get_assets_dir() / dest_name
    dest.write_bytes(content)

    # Caminho relativo ao diretorio de dados -> facil de migrar para a nuvem.
    settings.logo_path = f"assets/{dest_name}"
    db.commit()
    db.refresh(settings)
    return settings


def remove_logo(db: Session) -> Settings:
    settings = get_settings(db)
    _remove_old_logo(settings)
    settings.logo_path = None
    db.commit()
    db.refresh(settings)
    return settings


# Logo oficial embutida no app (já traz nome, título e CRP). Usada nos PDFs
# quando a usuária não enviou outra logo em Configuração.
OFFICIAL_LOGO = FRONTEND_DIR / "assets" / "logo-oficial.png"


def uploaded_logo_path(settings: Settings) -> Path | None:
    """Logo enviada em Configuração (ou None se não houver/não existir)."""
    if not settings.logo_path:
        return None
    p = get_data_dir() / settings.logo_path
    return p if p.exists() else None


def resolve_logo_path(settings: Settings) -> Path | None:
    """Logo a usar nos documentos: a enviada pela usuária ou a oficial do app."""
    p = uploaded_logo_path(settings)
    if p:
        return p
    return OFFICIAL_LOGO if OFFICIAL_LOGO.exists() else None


def logo_has_info(settings: Settings) -> bool:
    """A logo em uso já contém nome/título/CRP? (a oficial sempre contém)."""
    if uploaded_logo_path(settings):
        return bool(settings.logo_includes_info)
    return OFFICIAL_LOGO.exists()


def _remove_old_logo(settings: Settings) -> None:
    if settings.logo_path:
        old = get_data_dir() / settings.logo_path
        try:
            if old.exists():
                old.unlink()
        except OSError:
            pass


# ---------- Senha simples opcional ----------
def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return dk.hex()


def set_password(db: Session, password: str | None) -> Settings:
    settings = get_settings(db)
    if not password:
        settings.password_hash = None
    else:
        salt = secrets.token_hex(16)
        settings.password_hash = f"{salt}${_hash_password(password, salt)}"
    db.commit()
    db.refresh(settings)
    return settings


def verify_password(db: Session, password: str) -> bool:
    settings = get_settings(db)
    if not settings.password_hash:
        return True
    try:
        salt, expected = settings.password_hash.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_password(password, salt), expected)


# ---------- Integracao Google Agenda ----------
def update_google(db: Session, *, client_id: str | None, client_secret: str | None,
                  calendar_id: str | None, timezone: str | None) -> Settings:
    settings = get_settings(db)
    settings.google_client_id = (client_id or "").strip() or None
    # Mantem o secret anterior se vier vazio.
    if client_secret:
        settings.google_client_secret = client_secret.strip()
    settings.google_calendar_id = (calendar_id or "").strip() or "primary"
    settings.google_timezone = (timezone or "").strip() or "America/Sao_Paulo"
    db.commit()
    db.refresh(settings)
    return settings


# ---------- Recuperacao de senha por e-mail ----------
def update_recovery(db: Session, *, recovery_email: str | None, smtp_host: str | None,
                    smtp_port: int | None, smtp_user: str | None,
                    smtp_password: str | None) -> Settings:
    settings = get_settings(db)
    settings.recovery_email = (recovery_email or "").strip() or None
    settings.smtp_host = (smtp_host or "").strip() or None
    settings.smtp_port = smtp_port or None
    settings.smtp_user = (smtp_user or "").strip() or None
    # Mantem a senha SMTP anterior se vier vazia (nao apagar sem querer).
    if smtp_password:
        settings.smtp_password = smtp_password
    db.commit()
    db.refresh(settings)
    return settings


def request_password_reset(db: Session, email: str) -> dict:
    """Gera codigo de redefinicao. Envia por e-mail se houver SMTP; senao,
    libera redefinicao direta (app local, e-mail de recuperacao ja confere)."""
    settings = get_settings(db)
    if not settings.recovery_email:
        raise ValueError("Nenhum e-mail de recuperação configurado.")
    if (email or "").strip().lower() != settings.recovery_email.lower():
        raise ValueError("E-mail não confere com o de recuperação.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    settings.reset_code_hash = f"{salt}${_hash_password(code, salt)}"
    settings.reset_expires = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
    db.commit()

    if settings.smtp_host and settings.smtp_port:
        _send_email(
            settings,
            to=settings.recovery_email,
            subject="ProntoPsi — código de recuperação de senha",
            body=f"Seu código para redefinir a senha do ProntoPsi é: {code}\n\n"
                 f"Ele expira em 30 minutos. Se você não solicitou, ignore este e-mail.",
        )
        return {"sent": True, "direct": False, "email": _mask(settings.recovery_email)}
    # Sem servidor de e-mail: permite redefinir direto (uso local).
    return {"sent": False, "direct": True, "email": _mask(settings.recovery_email)}


def confirm_password_reset(db: Session, code: str, new_password: str) -> None:
    settings = get_settings(db)
    if not settings.reset_expires or not new_password:
        raise ValueError("Nenhuma redefinição em andamento.")
    if datetime.fromisoformat(settings.reset_expires) < datetime.utcnow():
        _clear_reset(db, settings)
        raise ValueError("Código expirado. Solicite novamente.")

    # Com SMTP, exige o codigo. Sem SMTP (local), a conferencia do e-mail no
    # pedido ja basta.
    if settings.smtp_host and settings.smtp_port:
        if not _check_code(settings, code):
            raise ValueError("Código incorreto.")

    salt = secrets.token_hex(16)
    settings.password_hash = f"{salt}${_hash_password(new_password, salt)}"
    _clear_reset(db, settings)


def _check_code(settings: Settings, code: str) -> bool:
    if not settings.reset_code_hash:
        return False
    try:
        salt, expected = settings.reset_code_hash.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_password(code or "", salt), expected)


def _clear_reset(db: Session, settings: Settings) -> None:
    settings.reset_code_hash = None
    settings.reset_expires = None
    db.commit()


def _mask(email: str) -> str:
    try:
        user, domain = email.split("@", 1)
    except ValueError:
        return email
    head = user[:2] if len(user) > 2 else user[:1]
    return f"{head}{'*' * max(1, len(user) - len(head))}@{domain}"


def _send_email(settings: Settings, *, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user or "prontopsi@localhost"
    msg["To"] = to
    msg.set_content(body)
    host, port = settings.smtp_host, int(settings.smtp_port)
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context()) as s:
                if settings.smtp_user:
                    s.login(settings.smtp_user, settings.smtp_password or "")
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls(context=ssl.create_default_context())
                if settings.smtp_user:
                    s.login(settings.smtp_user, settings.smtp_password or "")
                s.send_message(msg)
    except Exception as exc:
        raise ValueError(f"Falha ao enviar e-mail: {exc}") from exc
