"""Geração de documentos em PDF: recibo e declaração de comparecimento."""
from __future__ import annotations

import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Patient
from ..services import document_pdf_service, settings_service
from ..services.transfer_service import _slug

router = APIRouter(prefix="/api/doc-pdf", tags=["doc-pdf"])


class ReciboIn(BaseModel):
    patient_id: str | None = None
    payer: str = ""
    amount: float = 0.0
    reference: str = "atendimento psicológico"
    city: str = ""
    when: str | None = None  # 'YYYY-MM-DD'


class DeclaracaoIn(BaseModel):
    patient_id: str
    when: str                # 'YYYY-MM-DD'
    start: str = ""
    end: str = ""
    city: str = ""
    extra: str = ""


def _pdf_response(content: bytes, filename: str) -> StreamingResponse:
    disp = f"attachment; filename*=UTF-8''{quote(filename)}"
    return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                             headers={"Content-Disposition": disp})


@router.post("/recibo")
def recibo(payload: ReciboIn, db: Session = Depends(get_db)):
    settings = settings_service.get_settings(db)
    payer = payload.payer.strip()
    if not payer and payload.patient_id:
        p = db.get(Patient, payload.patient_id)
        if p:
            payer = p.name
    content = document_pdf_service.build_recibo(
        settings, payer=payer, amount=payload.amount,
        reference=payload.reference, city=payload.city, when_iso=payload.when,
    )
    base = _slug(payer) or "recibo"
    return _pdf_response(content, f"Recibo_{base}.pdf")


@router.post("/declaracao")
def declaracao(payload: DeclaracaoIn, db: Session = Depends(get_db)):
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    content = document_pdf_service.build_declaracao(
        settings_service.get_settings(db), patient, when_iso=payload.when,
        start=payload.start, end=payload.end, city=payload.city, extra=payload.extra,
    )
    base = _slug(patient.name) or "declaracao"
    return _pdf_response(content, f"Declaracao_{base}.pdf")
