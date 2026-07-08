"""Rotas de Pacientes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import PatientIn, PatientOut
from ..services import patients_service

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(search: str | None = None, db: Session = Depends(get_db)):
    return patients_service.list_patients(db, search)


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(payload: PatientIn, db: Session = Depends(get_db)):
    patient = patients_service.create_patient(db, payload.model_dump())
    return patients_service.get_patient_dict(db, patient.id)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = patients_service.get_patient_dict(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: str, payload: PatientIn, db: Session = Depends(get_db)):
    patient = patients_service.update_patient(db, patient_id, payload.model_dump())
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
    return patients_service.get_patient_dict(db, patient_id)


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    if not patients_service.delete_patient(db, patient_id):
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
