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
from ..models import (
    Anamnesis, Appointment, ClientNote, Document, FinanceEntry, Guardian, Patient, Receipt,
    Settings,
)
from ..utils import now_iso
from . import pdf_service, settings_service

EXPORT_SCHEMA = "1"


def export_dict(db: Session) -> dict:
    settings = settings_service.get_settings(db)
    patients = db.scalars(select(Patient).order_by(Patient.created_at)).all()
    anamneses = db.scalars(select(Anamnesis).order_by(Anamnesis.created_at)).all()
    appointments = db.scalars(select(Appointment).order_by(Appointment.created_at)).all()
    notes = db.scalars(select(ClientNote).order_by(ClientNote.created_at)).all()
    documents = db.scalars(select(Document).order_by(Document.created_at)).all()
    finance = db.scalars(select(FinanceEntry).order_by(FinanceEntry.created_at)).all()
    guardians = db.scalars(select(Guardian).order_by(Guardian.created_at)).all()
    receipts = db.scalars(select(Receipt).order_by(Receipt.number)).all()

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
            "legal_name": settings.legal_name,
            "cpf": settings.cpf,
            "offices": settings_service.get_offices(settings),
            "receipt_next": settings.receipt_next or 1,
        },
        "patients": [
            {
                "id": p.id,
                "name": p.name,
                "birth_date": p.birth_date,
                "sex": p.sex,
                "phones": p.phones,
                "email": p.email,
                "status": p.status,
                "notes": p.notes,
                "session_price_cents": p.session_price_cents,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in patients
        ],
        "guardians": [
            {
                "id": g.id, "patient_id": g.patient_id, "name": g.name,
                "kinship": g.kinship, "phone": g.phone, "email": g.email,
                "cpf": g.cpf, "is_primary": g.is_primary, "notes": g.notes,
                "created_at": g.created_at, "updated_at": g.updated_at,
            }
            for g in guardians
        ],
        "client_notes": [
            {
                "id": n.id, "patient_id": n.patient_id, "date": n.date,
                "title": n.title, "text": n.text,
                "created_at": n.created_at, "updated_at": n.updated_at,
            }
            for n in notes
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
                "evolution": ap.evolution,
                "created_at": ap.created_at,
                "updated_at": ap.updated_at,
            }
            for ap in appointments
        ],
        "documents": [
            {
                "id": d.id, "patient_id": d.patient_id, "filename": d.filename,
                "stored_path": d.stored_path, "size": d.size, "mime": d.mime,
                "created_at": d.created_at, "updated_at": d.updated_at,
            }
            for d in documents
        ],
        "finance_entries": [
            {
                "id": f.id, "kind": f.kind, "description": f.description,
                "category": f.category, "amount_cents": f.amount_cents,
                "currency": f.currency, "due_date": f.due_date, "paid": f.paid,
                "paid_date": f.paid_date, "recurrence": f.recurrence,
                "patient_id": f.patient_id, "appointment_id": f.appointment_id,
                "notes": f.notes,
                "created_at": f.created_at, "updated_at": f.updated_at,
            }
            for f in finance
        ],
        "receipts": [
            {
                "id": r.id, "number": r.number, "issued_on": r.issued_on,
                "patient_id": r.patient_id, "patient_name": r.patient_name,
                "payer": r.payer, "payer_cpf": r.payer_cpf, "payer_title": r.payer_title,
                "amount_cents": r.amount_cents, "sessions": r.sessions,
                "session_dates": r.session_dates, "service": r.service, "city": r.city,
                "created_at": r.created_at, "updated_at": r.updated_at,
            }
            for r in receipts
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

        # Arquivos dos documentos anexados (caminho relativo ao diretorio de dados).
        data_dir = get_data_dir()
        for d in db.scalars(select(Document)).all():
            f = data_dir / d.stored_path
            if f.exists():
                zf.write(str(f), d.stored_path)

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
        if "legal_name" in s:
            settings.legal_name = s.get("legal_name")
        if "cpf" in s:
            settings.cpf = s.get("cpf")
        if isinstance(s.get("offices"), list):
            settings.offices = json.dumps(s["offices"], ensure_ascii=False)
        if s.get("receipt_next"):
            settings.receipt_next = max(int(s["receipt_next"]), settings.receipt_next or 1)
        stats["settings"] = 1

    for p in payload.get("patients", []):
        obj = db.get(Patient, p["id"]) or Patient(id=p["id"])
        obj.name = p.get("name", "")
        obj.birth_date = p.get("birth_date")
        obj.sex = p.get("sex")
        obj.phones = p.get("phones")
        obj.email = p.get("email")
        obj.status = p.get("status", "ativo")
        obj.notes = p.get("notes")
        obj.session_price_cents = p.get("session_price_cents", 0)
        if p.get("created_at"):
            obj.created_at = p["created_at"]
        db.merge(obj)
        stats["patients"] += 1

    for g in payload.get("guardians", []):
        obj = db.get(Guardian, g["id"]) or Guardian(id=g["id"])
        obj.patient_id = g["patient_id"]
        obj.name = g.get("name", "")
        obj.kinship = g.get("kinship")
        obj.phone = g.get("phone")
        obj.email = g.get("email")
        obj.cpf = g.get("cpf")
        obj.is_primary = bool(g.get("is_primary"))
        obj.notes = g.get("notes")
        if g.get("created_at"):
            obj.created_at = g["created_at"]
        db.merge(obj)
        stats["guardians"] = stats.get("guardians", 0) + 1

    for n in payload.get("client_notes", []):
        obj = db.get(ClientNote, n["id"]) or ClientNote(id=n["id"])
        obj.patient_id = n["patient_id"]
        obj.date = n.get("date")
        obj.title = n.get("title")
        obj.text = n.get("text", "")
        if n.get("created_at"):
            obj.created_at = n["created_at"]
        db.merge(obj)
        stats["client_notes"] = stats.get("client_notes", 0) + 1

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
        obj.evolution = ap.get("evolution")
        if ap.get("created_at"):
            obj.created_at = ap["created_at"]
        db.merge(obj)
        stats["appointments"] = stats.get("appointments", 0) + 1

    for d in payload.get("documents", []):
        obj = db.get(Document, d["id"]) or Document(id=d["id"])
        obj.patient_id = d["patient_id"]
        obj.filename = d.get("filename", "arquivo")
        obj.stored_path = d.get("stored_path")
        obj.size = d.get("size", 0)
        obj.mime = d.get("mime")
        if d.get("created_at"):
            obj.created_at = d["created_at"]
        db.merge(obj)
        stats["documents"] = stats.get("documents", 0) + 1

    for f in payload.get("finance_entries", []):
        obj = db.get(FinanceEntry, f["id"]) or FinanceEntry(id=f["id"])
        obj.kind = f.get("kind", "receita")
        obj.description = f.get("description", "")
        obj.category = f.get("category", "")
        obj.amount_cents = f.get("amount_cents", 0)
        obj.currency = f.get("currency", "BRL")
        obj.due_date = f.get("due_date")
        obj.paid = bool(f.get("paid"))
        obj.paid_date = f.get("paid_date")
        obj.recurrence = f.get("recurrence", "nenhuma")
        obj.patient_id = f.get("patient_id")
        obj.appointment_id = f.get("appointment_id")
        obj.notes = f.get("notes")
        if f.get("created_at"):
            obj.created_at = f["created_at"]
        db.merge(obj)
        stats["finance_entries"] = stats.get("finance_entries", 0) + 1

    for r in payload.get("receipts", []):
        obj = db.get(Receipt, r["id"]) or Receipt(id=r["id"])
        for campo in ("number", "issued_on", "patient_id", "patient_name", "payer", "payer_cpf",
                      "payer_title", "amount_cents", "sessions", "session_dates", "service", "city"):
            if campo in r:
                setattr(obj, campo, r[campo])
        if r.get("created_at"):
            obj.created_at = r["created_at"]
        db.merge(obj)
        stats["receipts"] = stats.get("receipts", 0) + 1

    db.commit()
    return stats


def import_bytes(db: Session, filename: str, content: bytes) -> dict:
    """Aceita tanto .json quanto .zip exportado por este app."""
    name = (filename or "").lower()
    if name.endswith(".zip") or content[:2] == b"PK":
        data_dir = get_data_dir()
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            payload = json.loads(zf.read("data.json").decode("utf-8"))
            for info in zf.namelist():
                if info.endswith("/"):
                    continue
                if info.startswith("assets/"):
                    dest = get_assets_dir() / Path(info).name
                    dest.write_bytes(zf.read(info))
                    payload.setdefault("settings", {})["logo_path"] = f"assets/{dest.name}"
                elif info.startswith("documents/"):
                    # Restaura o arquivo do documento no mesmo caminho relativo.
                    dest = (data_dir / info).resolve()
                    if str(dest).startswith(str(data_dir.resolve())):
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(zf.read(info))
        return import_dict(db, payload)

    payload = json.loads(content.decode("utf-8"))
    return import_dict(db, payload)


def _slug(text: str) -> str:
    keep = [c if c.isalnum() else "_" for c in (text or "").strip()]
    return "".join(keep).strip("_")[:40]
