"""Regras dos documentos anexados ao cliente.

Os arquivos ficam em <diretório de dados>/documents/ com nome único; o banco
guarda o caminho RELATIVO (fácil de mover para um storage na nuvem depois).
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_data_dir
from ..models import Document, Patient
from ..utils import new_uuid


def _docs_dir() -> Path:
    d = get_data_dir() / "documents"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _to_dict(doc: Document) -> dict:
    return {
        "id": doc.id, "patient_id": doc.patient_id, "filename": doc.filename,
        "size": doc.size, "mime": doc.mime, "created_at": doc.created_at,
    }


# Lista os documentos de um paciente.
def list_documents(db: Session, patient_id: str) -> list[dict]:
    stmt = (select(Document).where(Document.patient_id == patient_id)
            .order_by(Document.created_at.desc()))
    return [_to_dict(d) for d in db.scalars(stmt).all()]


# Salva um arquivo enviado e registra no banco.
def save_document(db: Session, patient_id: str, filename: str, content: bytes,
                  mime: str | None) -> dict | None:
    if not db.get(Patient, patient_id):
        return None
    safe = Path(filename).name or "arquivo"
    stored_name = f"{new_uuid()}_{safe}"
    (_docs_dir() / stored_name).write_bytes(content)
    doc = Document(
        patient_id=patient_id, filename=safe,
        stored_path=f"documents/{stored_name}", size=len(content), mime=mime,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _to_dict(doc)


# Caminho absoluto do arquivo (para download).
def resolve_path(db: Session, doc_id: str) -> tuple[Path, Document] | None:
    doc = db.get(Document, doc_id)
    if not doc:
        return None
    p = get_data_dir() / doc.stored_path
    if not p.exists():
        return None
    return p, doc


def delete_document(db: Session, doc_id: str) -> bool:
    doc = db.get(Document, doc_id)
    if not doc:
        return False
    try:
        (get_data_dir() / doc.stored_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(doc)
    db.commit()
    return True
