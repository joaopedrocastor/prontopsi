"""Regras de negocio de Pacientes (camada de servico)."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..models import Anamnesis, Patient
from ..utils import calcular_idade


def _normaliza_sexo(sex: str | None) -> str | None:
    if not sex:
        return None
    s = sex.strip().upper()[:1]
    return s if s in ("F", "M") else None


def list_patients(db: Session, search: str | None = None) -> list[dict]:
    stmt = select(Patient)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Patient.name.ilike(like)))
    stmt = stmt.order_by(Patient.name.asc())
    patients = db.scalars(stmt).all()

    # Contagem de fichas por paciente numa unica consulta.
    counts = dict(
        db.execute(
            select(Anamnesis.patient_id, func.count(Anamnesis.id)).group_by(Anamnesis.patient_id)
        ).all()
    )
    return [_to_dict(p, counts.get(p.id, 0)) for p in patients]


def get_patient(db: Session, patient_id: str) -> Patient | None:
    return db.get(Patient, patient_id)


def get_patient_dict(db: Session, patient_id: str) -> dict | None:
    p = db.get(Patient, patient_id)
    if not p:
        return None
    count = db.scalar(
        select(func.count(Anamnesis.id)).where(Anamnesis.patient_id == patient_id)
    ) or 0
    return _to_dict(p, count)


def create_patient(db: Session, data: dict) -> Patient:
    patient = Patient(
        name=(data.get("name") or "").strip(),
        birth_date=(data.get("birth_date") or None),
        sex=_normaliza_sexo(data.get("sex")),
        phones=(data.get("phones") or None),
        notes=(data.get("notes") or None),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, patient_id: str, data: dict) -> Patient | None:
    patient = db.get(Patient, patient_id)
    if not patient:
        return None
    patient.name = (data.get("name") or "").strip()
    patient.birth_date = data.get("birth_date") or None
    patient.sex = _normaliza_sexo(data.get("sex"))
    patient.phones = data.get("phones") or None
    patient.notes = data.get("notes") or None
    db.commit()
    db.refresh(patient)
    return patient


def delete_patient(db: Session, patient_id: str) -> bool:
    patient = db.get(Patient, patient_id)
    if not patient:
        return False
    db.delete(patient)  # cascade remove as fichas
    db.commit()
    return True


def _to_dict(p: Patient, anamneses_count: int) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "birth_date": p.birth_date,
        "sex": p.sex,
        "phones": p.phones,
        "notes": p.notes,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "age": calcular_idade(p.birth_date),
        "anamneses_count": anamneses_count,
    }
