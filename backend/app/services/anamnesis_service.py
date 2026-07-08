"""Regras de negocio das Fichas de Anamnese (camada de servico)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import form_schema
from ..models import Anamnesis, Patient


def _prefill_from_patient(patient: Patient) -> dict:
    """Aproveita o cadastro do paciente para ja preencher a identificacao."""
    data: dict = {}
    if patient.name:
        data["nome"] = patient.name
    if patient.birth_date:
        data["data_nascimento"] = patient.birth_date
    if patient.sex:
        data["sexo"] = patient.sex
    if patient.phones:
        data["telefones"] = patient.phones
    return data


def create_anamnesis(db: Session, patient_id: str, data: dict | None = None) -> Anamnesis | None:
    patient = db.get(Patient, patient_id)
    if not patient:
        return None
    merged = _prefill_from_patient(patient)
    if data:
        merged.update(data)
    anamnesis = Anamnesis(
        patient_id=patient_id,
        form_version=form_schema.FORM_VERSION,
        status="rascunho",
        data=merged,
    )
    db.add(anamnesis)
    db.commit()
    db.refresh(anamnesis)
    return anamnesis


def get_anamnesis(db: Session, anamnesis_id: str) -> Anamnesis | None:
    return db.get(Anamnesis, anamnesis_id)


def update_anamnesis(db: Session, anamnesis_id: str, *, data: dict | None = None,
                     status: str | None = None) -> Anamnesis | None:
    anamnesis = db.get(Anamnesis, anamnesis_id)
    if not anamnesis:
        return None
    if data is not None:
        # Merge parcial: autosave envia apenas os campos alterados.
        merged = dict(anamnesis.data or {})
        merged.update(data)
        anamnesis.data = merged
    if status is not None:
        anamnesis.status = "concluida" if status == "concluida" else "rascunho"
    db.commit()
    db.refresh(anamnesis)
    return anamnesis


def duplicate_anamnesis(db: Session, anamnesis_id: str) -> Anamnesis | None:
    """Duplica para reavaliacao: copia os dados, volta status para rascunho."""
    original = db.get(Anamnesis, anamnesis_id)
    if not original:
        return None
    copy = Anamnesis(
        patient_id=original.patient_id,
        form_version=original.form_version,
        status="rascunho",
        data=dict(original.data or {}),
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


def delete_anamnesis(db: Session, anamnesis_id: str) -> bool:
    anamnesis = db.get(Anamnesis, anamnesis_id)
    if not anamnesis:
        return False
    db.delete(anamnesis)
    db.commit()
    return True


def list_anamneses(db: Session, patient_id: str | None = None) -> list[dict]:
    stmt = select(Anamnesis, Patient.name).join(Patient, Anamnesis.patient_id == Patient.id)
    if patient_id:
        stmt = stmt.where(Anamnesis.patient_id == patient_id)
    stmt = stmt.order_by(Anamnesis.updated_at.desc())
    rows = db.execute(stmt).all()
    return [_to_summary(a, patient_name) for a, patient_name in rows]


def _to_summary(a: Anamnesis, patient_name: str) -> dict:
    return {
        "id": a.id,
        "patient_id": a.patient_id,
        "patient_name": patient_name or "",
        "form_version": a.form_version,
        "status": a.status,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "missing_total": form_schema.missing_report(a.data).get("total", 0),
    }
