"""Regras de negocio da Agenda (camada de servico)."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Appointment, Patient


def _sync_google(db: Session, appt: Appointment) -> None:
    """Empurra para a Agenda Google, se conectada (best-effort, nunca falha)."""
    try:
        from . import google_service
        google_service.sync_appointment(db, appt)
    except Exception:
        pass


def _maybe_charge(db: Session, appt: Appointment) -> None:
    """Sessão marcada como realizada gera a cobrança do cliente (se tiver valor
    padrão e ainda não houver cobrança). Best-effort, nunca quebra o fluxo."""
    if appt.status != "realizada" or not appt.patient_id:
        return
    try:
        from . import finance_service
        patient = db.get(Patient, appt.patient_id)
        finance_service.create_session_charge(db, patient, appt)
    except Exception:
        pass


def _delete_google(db: Session, google_event_id: str | None) -> None:
    if not google_event_id:
        return
    try:
        from . import google_service
        google_service.delete_event(db, google_event_id)
    except Exception:
        pass


def _to_dict(a: Appointment, patient_name: str | None = None) -> dict:
    return {
        "id": a.id,
        "patient_id": a.patient_id,
        "patient_name": patient_name if patient_name is not None else (a.patient.name if a.patient else ""),
        "title": a.title or (a.patient.name if a.patient else ""),
        "start_at": a.start_at,
        "end_at": a.end_at,
        "status": a.status,
        "modality": a.modality,
        "color": a.color,
        "notes": a.notes,
        "evolution": a.evolution,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def list_appointments(db: Session, start: str | None = None, end: str | None = None,
                      patient_id: str | None = None) -> list[dict]:
    """Lista agendamentos, opcionalmente no intervalo [start, end) e por paciente."""
    stmt = select(Appointment, Patient.name).join(
        Patient, Appointment.patient_id == Patient.id, isouter=True
    )
    if start:
        stmt = stmt.where(Appointment.start_at >= start)
    if end:
        stmt = stmt.where(Appointment.start_at < end)
    if patient_id:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    stmt = stmt.order_by(Appointment.start_at.asc())
    return [_to_dict(a, name or "") for a, name in db.execute(stmt).all()]


def list_upcoming(db: Session, limit: int = 8) -> list[dict]:
    """Proximas consultas a partir de agora (para o alerta do painel)."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    stmt = (
        select(Appointment, Patient.name)
        .join(Patient, Appointment.patient_id == Patient.id, isouter=True)
        .where(Appointment.end_at >= now)
        .where(Appointment.status.notin_(["cancelada"]))
        .order_by(Appointment.start_at.asc())
        .limit(limit)
    )
    return [_to_dict(a, name or "") for a, name in db.execute(stmt).all()]


def get_appointment(db: Session, appointment_id: str) -> dict | None:
    a = db.get(Appointment, appointment_id)
    return _to_dict(a) if a else None


def create_appointment(db: Session, data: dict) -> dict:
    start = data["start_at"]
    end = data.get("end_at") or _default_end(start)
    title = (data.get("title") or "").strip()
    if not title and data.get("patient_id"):
        p = db.get(Patient, data["patient_id"])
        title = p.name if p else ""
    a = Appointment(
        patient_id=data.get("patient_id") or None,
        title=title,
        start_at=start,
        end_at=end,
        status=data.get("status") or "agendada",
        modality=data.get("modality"),
        color=data.get("color"),
        notes=data.get("notes"),
        evolution=data.get("evolution"),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    _sync_google(db, a)
    _maybe_charge(db, a)
    return _to_dict(a)


def update_appointment(db: Session, appointment_id: str, data: dict) -> dict | None:
    a = db.get(Appointment, appointment_id)
    if not a:
        return None
    for field in ("title", "start_at", "end_at", "status", "modality", "color", "notes", "evolution"):
        if field in data and data[field] is not None:
            setattr(a, field, data[field])
    if "patient_id" in data:
        a.patient_id = data["patient_id"] or None
    db.commit()
    db.refresh(a)
    _sync_google(db, a)
    _maybe_charge(db, a)
    return _to_dict(a)


def delete_appointment(db: Session, appointment_id: str) -> bool:
    a = db.get(Appointment, appointment_id)
    if not a:
        return False
    google_event_id = a.google_event_id
    db.delete(a)
    db.commit()
    _delete_google(db, google_event_id)
    return True


def _default_end(start: str) -> str:
    try:
        dt = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
        return (dt + timedelta(minutes=50)).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return start
