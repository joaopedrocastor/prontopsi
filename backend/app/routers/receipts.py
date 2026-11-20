"""Rotas dos recibos emitidos (lista, criar, editar, PDF, próximo número)."""
from __future__ import annotations

import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import receipts_service
from ..services.transfer_service import _slug

router = APIRouter(prefix="/api/receipts", tags=["receipts"])


class ReceiptIn(BaseModel):
    patient_id: str | None = None
    patient_name: str = ""
    payer: str = ""
    payer_cpf: str = ""
    payer_title: str = ""            # 'Sr.' | 'Sra.' | ''
    amount: float = 0.0
    sessions: int | None = None
    session_dates: list[str] = []
    service: str = ""
    city: str = ""
    issued_on: str | None = None     # data do recibo 'YYYY-MM-DD'


@router.get("")
def list_receipts(start: str | None = None, end: str | None = None,
                  patient_id: str | None = None, db: Session = Depends(get_db)):
    return receipts_service.list_receipts(db, start, end, patient_id)


@router.get("/next-number")
def next_number(db: Session = Depends(get_db)) -> dict:
    return {"next": receipts_service.next_number(db),
            "has_receipts": receipts_service.has_receipts(db)}


@router.post("", status_code=201)
def create_receipt(payload: ReceiptIn, db: Session = Depends(get_db)):
    if not payload.amount:
        raise HTTPException(status_code=400, detail="Informe o valor.")
    return receipts_service.create(db, payload.model_dump())


@router.put("/{receipt_id}")
def update_receipt(receipt_id: str, payload: ReceiptIn, db: Session = Depends(get_db)):
    r = receipts_service.update(db, receipt_id, payload.model_dump())
    if not r:
        raise HTTPException(status_code=404, detail="Recibo não encontrado.")
    return r


@router.get("/{receipt_id}/pdf")
def receipt_pdf(receipt_id: str, db: Session = Depends(get_db)):
    r = receipts_service.get(db, receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Recibo não encontrado.")
    content = receipts_service.build_pdf(db, r)
    nome = f"Recibo_{r.number:03d}_{_slug(r.payer) or 'recibo'}.pdf"
    return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"})
