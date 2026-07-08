"""Rotas de sistema: backup, restauracao, exportacao/importacao e salvar PDF.

As operacoes que envolvem escolher pasta/arquivo no computador recebem o
caminho ja escolhido pela usuaria (via dialogo nativo do pywebview, no
desktop) ou aceitam upload (no navegador).
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import APP_VERSION, get_data_dir
from ..database import get_db
from ..services import (
    anamnesis_service,
    backup_service,
    pdf_service,
    settings_service,
    transfer_service,
    update_service,
)
from ..services.transfer_service import _slug

router = APIRouter(prefix="/api/system", tags=["system"])


class BackupIn(BaseModel):
    dest_dir: str


class RestoreIn(BaseModel):
    src_file: str


class ExportToIn(BaseModel):
    path: str
    format: str = "zip"  # 'zip' | 'json'


class SavePdfIn(BaseModel):
    anamnesis_id: str
    path: str


@router.get("/info")
def info() -> dict:
    return {"data_dir": str(get_data_dir()), "version": APP_VERSION}


# Verifica no GitHub (repo prontopsi-releases) se há uma versão mais nova.
@router.get("/check-update")
def check_update() -> dict:
    return update_service.check_update()


# ---------- Backup ----------
@router.post("/backup")
def backup(payload: BackupIn) -> dict:
    try:
        target = backup_service.create_backup(payload.dest_dir)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"path": str(target)}


@router.post("/restore")
def restore(payload: RestoreIn) -> dict:
    try:
        backup_service.restore_backup(payload.src_file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "restart_required": True}


# ---------- Exportacao completa (migracao para a nuvem) ----------
@router.get("/export")
def export_download(format: str = "zip", db: Session = Depends(get_db)):
    if format == "json":
        payload = transfer_service.export_dict(db)
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content), media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="anamnese_dados.json"'},
        )
    content = transfer_service.export_zip(db)
    return StreamingResponse(
        io.BytesIO(content), media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="anamnese_dados.zip"'},
    )


@router.post("/export-to")
def export_to(payload: ExportToIn, db: Session = Depends(get_db)) -> dict:
    dest = Path(payload.path).expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if payload.format == "json":
        data = json.dumps(transfer_service.export_dict(db), ensure_ascii=False, indent=2)
        dest.write_text(data, encoding="utf-8")
    else:
        dest.write_bytes(transfer_service.export_zip(db))
    return {"path": str(dest)}


@router.post("/import")
async def import_data(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    try:
        stats = transfer_service.import_bytes(db, file.filename or "", content)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao importar: {exc}") from exc
    return {"ok": True, "imported": stats}


# ---------- Salvar PDF em caminho escolhido ----------
@router.post("/save-pdf")
def save_pdf(payload: SavePdfIn, db: Session = Depends(get_db)) -> dict:
    anamnesis = anamnesis_service.get_anamnesis(db, payload.anamnesis_id)
    if not anamnesis:
        raise HTTPException(status_code=404, detail="Ficha não encontrada.")
    settings = settings_service.get_settings(db)
    pdf_bytes = pdf_service.build_pdf(anamnesis, anamnesis.patient, settings)
    dest = Path(payload.path).expanduser()
    if dest.suffix.lower() != ".pdf":
        dest = dest.with_suffix(".pdf")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(pdf_bytes)
    return {"path": str(dest)}
