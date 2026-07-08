"""Rotas de Configuracoes: identidade visual, logo e senha simples."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import RecoveryIn, ResetConfirmIn, ResetRequestIn, SettingsIn, SettingsOut
from ..services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_out(settings) -> SettingsOut:
    return SettingsOut(
        id=settings.id,
        professional_name=settings.professional_name,
        professional_title=settings.professional_title,
        crp=settings.crp,
        logo_path=settings.logo_path,
        logo_includes_info=bool(settings.logo_includes_info),
        has_password=bool(settings.password_hash),
        recovery_email=settings.recovery_email,
        has_smtp=bool(settings.smtp_host and settings.smtp_port),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _to_out(settings_service.get_settings(db))


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsIn, db: Session = Depends(get_db)):
    settings = settings_service.update_settings(
        db,
        professional_name=payload.professional_name,
        professional_title=payload.professional_title,
        crp=payload.crp,
        logo_includes_info=payload.logo_includes_info,
    )
    return _to_out(settings)


@router.post("/logo", response_model=SettingsOut)
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    try:
        settings = settings_service.save_logo(db, filename=file.filename or "logo.png",
                                              content=content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(settings)


@router.delete("/logo", response_model=SettingsOut)
def delete_logo(db: Session = Depends(get_db)):
    return _to_out(settings_service.remove_logo(db))


@router.get("/logo/image")
def get_logo_image(db: Session = Depends(get_db)):
    settings = settings_service.get_settings(db)
    path = settings_service.resolve_logo_path(settings)
    if not path:
        raise HTTPException(status_code=404, detail="Sem logo.")
    return FileResponse(str(path))


# ---------- Senha simples opcional ----------
class PasswordIn(BaseModel):
    password: str | None = None


@router.post("/password", response_model=SettingsOut)
def set_password(payload: PasswordIn, db: Session = Depends(get_db)):
    return _to_out(settings_service.set_password(db, payload.password))


@router.post("/password/verify")
def verify_password(payload: PasswordIn, db: Session = Depends(get_db)) -> dict:
    ok = settings_service.verify_password(db, payload.password or "")
    return {"ok": ok}


# ---------- Recuperacao de senha por e-mail ----------
@router.put("/recovery", response_model=SettingsOut)
def update_recovery(payload: RecoveryIn, db: Session = Depends(get_db)):
    settings = settings_service.update_recovery(
        db,
        recovery_email=payload.recovery_email,
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        smtp_user=payload.smtp_user,
        smtp_password=payload.smtp_password,
    )
    return _to_out(settings)


@router.post("/password/reset-request")
def reset_request(payload: ResetRequestIn, db: Session = Depends(get_db)) -> dict:
    try:
        return settings_service.request_password_reset(db, payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/password/reset-confirm")
def reset_confirm(payload: ResetConfirmIn, db: Session = Depends(get_db)) -> dict:
    try:
        settings_service.confirm_password_reset(db, payload.code, payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}
