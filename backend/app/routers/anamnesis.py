"""Rotas de Fichas de Anamnese."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..form_schema import missing_report
from ..database import get_db
from ..schemas import AnamnesisCreate, AnamnesisOut, AnamnesisSummary, AnamnesisUpdate
from ..services import anamnesis_service, pdf_service, settings_service
from ..services.transfer_service import _slug

router = APIRouter(prefix="/api/anamneses", tags=["anamneses"])


@router.get("", response_model=list[AnamnesisSummary])
def list_anamneses(patient_id: str | None = None, db: Session = Depends(get_db)):
    return anamnesis_service.list_anamneses(db, patient_id)


@router.post("", response_model=AnamnesisOut, status_code=201)
def create_anamnesis(payload: AnamnesisCreate, db: Session = Depends(get_db)):
    anamnesis = anamnesis_service.create_anamnesis(db, payload.patient_id, payload.data)
    if not anamnesis:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
    return anamnesis


@router.get("/{anamnesis_id}", response_model=AnamnesisOut)
def get_anamnesis(anamnesis_id: str, db: Session = Depends(get_db)):
    anamnesis = anamnesis_service.get_anamnesis(db, anamnesis_id)
    if not anamnesis:
        raise HTTPException(status_code=404, detail="Ficha não encontrada.")
    return anamnesis


@router.patch("/{anamnesis_id}", response_model=AnamnesisOut)
def update_anamnesis(anamnesis_id: str, payload: AnamnesisUpdate, db: Session = Depends(get_db)):
    anamnesis = anamnesis_service.update_anamnesis(
        db, anamnesis_id, data=payload.data, status=payload.status
    )
    if not anamnesis:
        raise HTTPException(status_code=404, detail="Ficha não encontrada.")
    return anamnesis


@router.post("/{anamnesis_id}/duplicate", response_model=AnamnesisOut, status_code=201)
def duplicate_anamnesis(anamnesis_id: str, db: Session = Depends(get_db)):
    copy = anamnesis_service.duplicate_anamnesis(db, anamnesis_id)
    if not copy:
        raise HTTPException(status_code=404, detail="Ficha não encontrada.")
    return copy


@router.delete("/{anamnesis_id}", status_code=204)
def delete_anamnesis(anamnesis_id: str, db: Session = Depends(get_db)):
    if not anamnesis_service.delete_anamnesis(db, anamnesis_id):
        raise HTTPException(status_code=404, detail="Ficha não encontrada.")


@router.get("/{anamnesis_id}/missing")
def missing(anamnesis_id: str, db: Session = Depends(get_db)) -> dict:
    """Relatorio de campos vazios (aviso nao bloqueante)."""
    anamnesis = anamnesis_service.get_anamnesis(db, anamnesis_id)
    if not anamnesis:
        raise HTTPException(status_code=404, detail="Ficha não encontrada.")
    return missing_report(anamnesis.data)


@router.get("/{anamnesis_id}/pdf")
def download_pdf(anamnesis_id: str, db: Session = Depends(get_db)):
    """Download direto do PDF (funciona no navegador e na janela desktop)."""
    anamnesis = anamnesis_service.get_anamnesis(db, anamnesis_id)
    if not anamnesis:
        raise HTTPException(status_code=404, detail="Ficha não encontrada.")
    patient = anamnesis.patient
    settings = settings_service.get_settings(db)
    pdf_bytes = pdf_service.build_pdf(anamnesis, patient, settings)

    fname = f"anamnese_{_slug(patient.name) or 'ficha'}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{fname}"'}
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)
