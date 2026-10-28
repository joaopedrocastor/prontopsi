"""Regras de negocio de Responsaveis (guardians) do cliente."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Guardian, Patient

_FIELDS = ("name", "kinship", "phone", "email", "cpf", "notes")


def _to_dict(g: Guardian) -> dict:
    return {
        "id": g.id,
        "patient_id": g.patient_id,
        "name": g.name or "",
        "kinship": g.kinship,
        "phone": g.phone,
        "email": g.email,
        "cpf": g.cpf,
        "is_primary": bool(g.is_primary),
        "notes": g.notes,
        "created_at": g.created_at,
        "updated_at": g.updated_at,
    }


def list_guardians(db: Session, patient_id: str) -> list[dict]:
    stmt = (select(Guardian).where(Guardian.patient_id == patient_id)
            .order_by(Guardian.is_primary.desc(), Guardian.name.asc()))
    return [_to_dict(g) for g in db.scalars(stmt).all()]


def _clear_primary(db: Session, patient_id: str, keep_id: str | None = None) -> None:
    for g in db.scalars(select(Guardian).where(Guardian.patient_id == patient_id,
                                               Guardian.is_primary == True)).all():  # noqa: E712
        if g.id != keep_id:
            g.is_primary = False


def create_guardian(db: Session, patient_id: str, data: dict) -> dict | None:
    if not db.get(Patient, patient_id):
        return None
    primary = bool(data.get("is_primary"))
    if primary:
        _clear_primary(db, patient_id)
    g = Guardian(
        patient_id=patient_id,
        name=(data.get("name") or "").strip(),
        kinship=data.get("kinship"),
        phone=data.get("phone"),
        email=data.get("email"),
        cpf=data.get("cpf"),
        is_primary=primary,
        notes=data.get("notes"),
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return _to_dict(g)


def update_guardian(db: Session, guardian_id: str, data: dict) -> dict | None:
    g = db.get(Guardian, guardian_id)
    if not g:
        return None
    for field in _FIELDS:
        if field in data:
            setattr(g, field, data[field])
    if "is_primary" in data:
        g.is_primary = bool(data["is_primary"])
        if g.is_primary:
            _clear_primary(db, g.patient_id, keep_id=g.id)
    db.commit()
    db.refresh(g)
    return _to_dict(g)


def delete_guardian(db: Session, guardian_id: str) -> bool:
    g = db.get(Guardian, guardian_id)
    if not g:
        return False
    db.delete(g)
    db.commit()
    return True
