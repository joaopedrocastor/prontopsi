"""Recibos emitidos: numeração contínua automática, salvar, editar e gerar PDF.

O número é atribuído pelo sistema no momento em que o recibo é salvo e nunca
muda depois (editar um recibo mantém o número). O próximo número é o maior
entre "último emitido + 1" e o número inicial de Configuração (útil para
continuar a numeração de recibos feitos antes do app).
"""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Patient, Receipt
from . import document_pdf_service, settings_service

_CAMPOS = ("patient_name", "payer", "payer_cpf", "payer_title", "service", "city")


def _cents(v: float | None) -> int:
    return int(round((v or 0) * 100))


def _datas(valor) -> list[str]:
    return sorted({str(d)[:10] for d in (valor or []) if d})


def to_dict(r: Receipt) -> dict:
    try:
        datas = json.loads(r.session_dates or "[]")
    except ValueError:
        datas = []
    return {
        "id": r.id,
        "number": r.number,
        "issued_on": r.issued_on,
        "patient_id": r.patient_id,
        "patient_name": r.patient_name or "",
        "payer": r.payer or "",
        "payer_cpf": r.payer_cpf or "",
        "payer_title": r.payer_title or "",
        "amount": round((r.amount_cents or 0) / 100, 2),
        "sessions": r.sessions,
        "session_dates": datas,
        "service": r.service or "",
        "city": r.city or "",
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def has_receipts(db: Session) -> bool:
    return (db.scalar(select(func.count(Receipt.id))) or 0) > 0


def next_number(db: Session) -> int:
    ultimo = db.scalar(select(func.max(Receipt.number))) or 0
    inicial = settings_service.get_settings(db).receipt_next or 1
    return max(ultimo + 1, inicial)


def list_receipts(db: Session, start: str | None = None, end: str | None = None,
                  patient_id: str | None = None) -> list[dict]:
    stmt = select(Receipt)
    if start:
        stmt = stmt.where(Receipt.issued_on >= start)
    if end:
        stmt = stmt.where(Receipt.issued_on <= end)
    if patient_id:
        stmt = stmt.where(Receipt.patient_id == patient_id)
    stmt = stmt.order_by(Receipt.number.desc())
    return [to_dict(r) for r in db.scalars(stmt).all()]


def get(db: Session, receipt_id: str) -> Receipt | None:
    return db.get(Receipt, receipt_id)


def _aplicar(r: Receipt, data: dict) -> None:
    for campo in _CAMPOS:
        if campo in data and data[campo] is not None:
            setattr(r, campo, str(data[campo]).strip())
    if "patient_id" in data:
        r.patient_id = data["patient_id"] or None
    if data.get("issued_on"):
        r.issued_on = data["issued_on"][:10]
    if "amount" in data and data["amount"] is not None:
        r.amount_cents = _cents(data["amount"])
    if "sessions" in data:
        r.sessions = data["sessions"] or None
    if "session_dates" in data:
        r.session_dates = json.dumps(_datas(data["session_dates"]))


def create(db: Session, data: dict) -> dict:
    r = Receipt(number=next_number(db), issued_on=date.today().isoformat())
    _aplicar(r, data)
    db.add(r)
    db.commit()
    db.refresh(r)
    # Mantém a configuração em dia (o próximo sugerido nunca volta).
    settings_service.register_receipt_number(db, r.number)
    return to_dict(r)


def update(db: Session, receipt_id: str, data: dict) -> dict | None:
    r = db.get(Receipt, receipt_id)
    if not r:
        return None
    _aplicar(r, data)  # o número nunca muda
    db.commit()
    db.refresh(r)
    return to_dict(r)


def build_pdf(db: Session, r: Receipt) -> bytes:
    """Gera o PDF a partir do recibo salvo (com a logo/endereços atuais)."""
    settings = settings_service.get_settings(db)
    d = to_dict(r)
    patient = db.get(Patient, r.patient_id) if r.patient_id else None
    return document_pdf_service.build_recibo(
        settings, payer=d["payer"], amount=d["amount"], city=d["city"],
        when_iso=d["issued_on"], number=d["number"], payer_cpf=d["payer_cpf"],
        payer_title=d["payer_title"],
        patient_name=d["patient_name"] or (patient.name if patient else ""),
        patient_sex=(patient.sex if patient else "") or "",
        sessions=d["sessions"], session_dates=d["session_dates"], service=d["service"],
        office=settings_service.find_office(settings, d["city"]),
    )
