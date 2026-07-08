"""Exportacao / importacao completa dos dados (mecanismo oficial de migracao).

Gera um JSON (ou ZIP com JSON + logo + PDFs) com pacientes, fichas e
configuracoes. Esse arquivo e o caminho para levar tudo para a versao web sem
perda de dados. A importacao faz upsert por UUID, evitando conflitos.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_assets_dir, get_data_dir
from ..form_schema import FORM_VERSION
from ..models import Anamnesis, Appointment, Patient, Settings
from ..utils import now_iso
from . import pdf_service, settings_service

EXPORT_SCHEMA = "1"


def export_dict(db: Session) -> dict:
    settings = settings_service.get_settings(db)
    patients = db.scalars(select(Patient).order_by(Patient.created_at)).all()
    anamneses = db.scalars(select(Anamnesis).order_by(Anamnesis.created_at)).all()
    appointments = db.scalars(select(Appointment).order_by(Appointment.created_at)).all()

    return {
        "app": "AnamneseInfantil",
        "export_schema": EXPORT_SCHEMA,
        "form_version": FORM_VERSION,
        "exported_at": now_iso(),
        "settings": {
            "id": settings.id,
            "professional_name": settings.professional_name,
            "professional_title": settings.professional_title,
            "crp": settings.crp,
            "logo_path": settings.logo_path,
        },
        "patients": [
            {
                "id": p.id,
                "name": p.name,
                "birth_date": p.birth_date,
                "sex": p.sex,
                "phones": p.phones,
                "notes": p.notes,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in patients
        ],
        "anamneses": [
            {
                "id": a.id,
                "patient_id": a.patient_id,
                "form_version": a.form_version,
                "status": a.status,
                "data": a.data or {},
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
            for a in anamneses
        ],
        "appointments": [
            {
                "id": ap.id,
                "patient_id": ap.patient_id,
                "title": ap.title,
                "start_at": ap.start_at,
                "end_at": ap.end_at,
                "status": ap.status,
                "modality": ap.modality,
                "color": ap.color,
                "notes": ap.notes,
                "created_at": ap.created_at,
                "updated_at": ap.updated_at,
            }
            for ap in appointments
        ],
    }


def export_zip(db: Session, include_pdfs: bool = True) -> bytes:
    """ZIP com data.json + logo + PDFs de todas as fichas."""
    payload = export_dict(db)
    settings = settings_service.get_settings(db)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(payload, ensure_ascii=False, indent=2))

        logo = settings_service.resolve_logo_path(settings)
        if logo:
            zf.write(str(logo), f"assets/{logo.name}")

        if include_pdfs:
            patients = {p.id: p for p in db.scalars(select(Patient)).all()}
            for a in db.scalars(select(Anamnesis)).all():
                patient = patients.get(a.patient_id)
                if not patient:
                    continue
                try:
                    pdf_bytes = pdf_service.build_pdf(a, patient, settings)
                    safe = _slug(patient.name) or "ficha"
                    zf.writestr(f"pdfs/{safe}_{a.id[:8]}.pdf", pdf_bytes)
                except Exception:
                    # Um PDF com erro nao deve impedir o backup do restante.
                    continue

    return buffer.getvalue()


def import_dict(db: Session, payload: dict) -> dict:
    """Upsert por UUID. Retorna contagem do que foi importado."""
    if not isinstance(payload, dict) or "patients" not in payload:
        raise ValueError("Arquivo de importação inválido.")

    stats = {"patients": 0, "anamneses": 0, "settings": 0}

    # Configuracoes (identidade visual)
    s = payload.get("settings")
    if isinstance(s, dict):
        settings = settings_service.get_settings(db)
        settings.professional_name = s.get("professional_name", settings.professional_name)
        settings.professional_title = s.get("professional_title", settings.professional_title)
        settings.crp = s.get("crp", settings.crp)
        if s.get("logo_path"):
            settings.logo_path = s["logo_path"]
        stats["settings"] = 1

    for p in payload.get("patients", []):
        obj = db.get(Patient, p["id"]) or Patient(id=p["id"])
        obj.name = p.get("name", "")
        obj.birth_date = p.get("birth_date")
        obj.sex = p.get("sex")
        obj.phones = p.get("phones")
        obj.notes = p.get("notes")
        if p.get("created_at"):
            obj.created_at = p["created_at"]
        db.merge(obj)
        stats["patients"] += 1

    for a in payload.get("anamneses", []):
        obj = db.get(Anamnesis, a["id"]) or Anamnesis(id=a["id"])
        obj.patient_id = a["patient_id"]
        obj.form_version = a.get("form_version", FORM_VERSION)
        obj.status = a.get("status", "rascunho")
        obj.data = a.get("data", {})
        if a.get("created_at"):
            obj.created_at = a["created_at"]
        db.merge(obj)
        stats["anamneses"] += 1

    for ap in payload.get("appointments", []):
        obj = db.get(Appointment, ap["id"]) or Appointment(id=ap["id"])
        obj.patient_id = ap.get("patient_id")
        obj.title = ap.get("title", "")
        obj.start_at = ap.get("start_at")
        obj.end_at = ap.get("end_at")
        obj.status = ap.get("status", "agendada")
        obj.modality = ap.get("modality")
        obj.color = ap.get("color")
        obj.notes = ap.get("notes")
        if ap.get("created_at"):
            obj.created_at = ap["created_at"]
        db.merge(obj)
        stats["appointments"] = stats.get("appointments", 0) + 1

    db.commit()
    return stats


def import_bytes(db: Session, filename: str, content: bytes) -> dict:
    """Aceita tanto .json quanto .zip exportado por este app."""
    name = (filename or "").lower()
    if name.endswith(".zip") or content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            payload = json.loads(zf.read("data.json").decode("utf-8"))
            # Restaura logo, se houver.
            for info in zf.namelist():
                if info.startswith("assets/") and not info.endswith("/"):
                    dest = get_assets_dir() / Path(info).name
                    dest.write_bytes(zf.read(info))
                    rel = f"assets/{dest.name}"
                    payload.setdefault("settings", {})["logo_path"] = rel
        return import_dict(db, payload)

    payload = json.loads(content.decode("utf-8"))
    return import_dict(db, payload)


def _slug(text: str) -> str:
    keep = [c if c.isalnum() else "_" for c in (text or "").strip()]
    return "".join(keep).strip("_")[:40]
