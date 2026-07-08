"""Rotas da integracao com a Agenda Google (opcional)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import google_service, settings_service

router = APIRouter(prefix="/api/google", tags=["google"])


class GoogleConfigIn(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    calendar_id: str | None = "primary"
    timezone: str | None = "America/Sao_Paulo"


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    return google_service.status(db)


@router.put("/config")
def save_config(payload: GoogleConfigIn, db: Session = Depends(get_db)) -> dict:
    settings_service.update_google(
        db,
        client_id=payload.client_id,
        client_secret=payload.client_secret,
        calendar_id=payload.calendar_id,
        timezone=payload.timezone,
    )
    return google_service.status(db)


@router.post("/connect")
def connect(db: Session = Depends(get_db)) -> dict:
    """Inicia o fluxo OAuth (abre o navegador). Bloqueia ate a autorizacao."""
    try:
        google_service.connect(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # falha do fluxo OAuth
        raise HTTPException(status_code=400, detail=f"Falha ao conectar: {exc}") from exc
    return google_service.status(db)


@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db)) -> dict:
    google_service.disconnect()
    return google_service.status(db)
