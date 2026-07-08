"""Regras da timeline de anotações do cliente."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ClientNote, Patient


def _to_dict(n: ClientNote) -> dict:
    return {
        "id": n.id, "patient_id": n.patient_id, "date": n.date,
        "title": n.title, "text": n.text,
        "created_at": n.created_at, "updated_at": n.updated_at,
    }


# Lista as anotações de um paciente, da mais recente para a mais antiga.
def list_notes(db: Session, patient_id: str) -> list[dict]:
    stmt = (select(ClientNote).where(ClientNote.patient_id == patient_id)
            .order_by(ClientNote.date.desc(), ClientNote.created_at.desc()))
    return [_to_dict(n) for n in db.scalars(stmt).all()]


# Cria uma anotação nova na timeline (data padrão = hoje).
def create_note(db: Session, patient_id: str, data: dict) -> dict | None:
    if not db.get(Patient, patient_id):
        return None
    note = ClientNote(
        patient_id=patient_id,
        date=(data.get("date") or date.today().isoformat()),
        title=(data.get("title") or None),
        text=(data.get("text") or ""),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _to_dict(note)


def update_note(db: Session, note_id: str, data: dict) -> dict | None:
    note = db.get(ClientNote, note_id)
    if not note:
        return None
    if data.get("date"):
        note.date = data["date"]
    if "title" in data:
        note.title = data.get("title") or None
    if "text" in data:
        note.text = data.get("text") or ""
    db.commit()
    db.refresh(note)
    return _to_dict(note)


def delete_note(db: Session, note_id: str) -> bool:
    note = db.get(ClientNote, note_id)
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True
