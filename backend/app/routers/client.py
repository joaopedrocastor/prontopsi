"""Rotas da Ficha de Cliente: timeline de anotações e documentos."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import DocumentOut, GuardianIn, GuardianOut, NoteIn, NoteOut
from ..services import documents_service, guardians_service, notes_service

router = APIRouter(prefix="/api", tags=["client"])


# ---------- Timeline de anotações ----------
@router.get("/patients/{patient_id}/notes", response_model=list[NoteOut])
def list_notes(patient_id: str, db: Session = Depends(get_db)):
    return notes_service.list_notes(db, patient_id)


@router.post("/patients/{patient_id}/notes", response_model=NoteOut, status_code=201)
def create_note(patient_id: str, payload: NoteIn, db: Session = Depends(get_db)):
    note = notes_service.create_note(db, patient_id, payload.model_dump())
    if not note:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
    return note


@router.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: str, payload: NoteIn, db: Session = Depends(get_db)):
    note = notes_service.update_note(db, note_id, payload.model_dump(exclude_unset=True))
    if not note:
        raise HTTPException(status_code=404, detail="Anotação não encontrada.")
    return note


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: str, db: Session = Depends(get_db)):
    if not notes_service.delete_note(db, note_id):
        raise HTTPException(status_code=404, detail="Anotação não encontrada.")


# ---------- Responsáveis ----------
@router.get("/patients/{patient_id}/guardians", response_model=list[GuardianOut])
def list_guardians(patient_id: str, db: Session = Depends(get_db)):
    return guardians_service.list_guardians(db, patient_id)


@router.post("/patients/{patient_id}/guardians", response_model=GuardianOut, status_code=201)
def create_guardian(patient_id: str, payload: GuardianIn, db: Session = Depends(get_db)):
    g = guardians_service.create_guardian(db, patient_id, payload.model_dump())
    if not g:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
    return g


@router.patch("/guardians/{guardian_id}", response_model=GuardianOut)
def update_guardian(guardian_id: str, payload: GuardianIn, db: Session = Depends(get_db)):
    g = guardians_service.update_guardian(db, guardian_id, payload.model_dump(exclude_unset=True))
    if not g:
        raise HTTPException(status_code=404, detail="Responsável não encontrado.")
    return g


@router.delete("/guardians/{guardian_id}", status_code=204)
def delete_guardian(guardian_id: str, db: Session = Depends(get_db)):
    if not guardians_service.delete_guardian(db, guardian_id):
        raise HTTPException(status_code=404, detail="Responsável não encontrado.")


# ---------- Documentos ----------
@router.get("/patients/{patient_id}/documents", response_model=list[DocumentOut])
def list_documents(patient_id: str, db: Session = Depends(get_db)):
    return documents_service.list_documents(db, patient_id)


@router.post("/patients/{patient_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(patient_id: str, file: UploadFile = File(...),
                          db: Session = Depends(get_db)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    doc = documents_service.save_document(db, patient_id, file.filename or "arquivo",
                                          content, file.content_type)
    if not doc:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
    return doc


@router.get("/documents/{doc_id}")
def download_document(doc_id: str, db: Session = Depends(get_db)):
    found = documents_service.resolve_path(db, doc_id)
    if not found:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    path, doc = found
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc.filename)}"}
    return FileResponse(str(path), media_type=doc.mime or "application/octet-stream",
                        headers=headers)


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    if not documents_service.delete_document(db, doc_id):
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
