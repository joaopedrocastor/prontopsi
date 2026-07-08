"""Rotas da Agenda (agendamentos/sessoes)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AppointmentIn, AppointmentOut, AppointmentUpdate
from ..services import appointments_service

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentOut])
def list_appointments(start: str | None = None, end: str | None = None,
                      patient_id: str | None = None, db: Session = Depends(get_db)):
    return appointments_service.list_appointments(db, start, end, patient_id)


@router.get("/upcoming", response_model=list[AppointmentOut])
def upcoming(limit: int = 8, db: Session = Depends(get_db)):
    return appointments_service.list_upcoming(db, limit)


@router.post("", response_model=AppointmentOut, status_code=201)
def create_appointment(payload: AppointmentIn, db: Session = Depends(get_db)):
    return appointments_service.create_appointment(db, payload.model_dump())


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: str, db: Session = Depends(get_db)):
    a = appointments_service.get_appointment(db, appointment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return a


@router.patch("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: str, payload: AppointmentUpdate,
                       db: Session = Depends(get_db)):
    a = appointments_service.update_appointment(db, appointment_id,
                                                payload.model_dump(exclude_unset=True))
    if not a:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return a


@router.delete("/{appointment_id}", status_code=204)
def delete_appointment(appointment_id: str, db: Session = Depends(get_db)):
    if not appointments_service.delete_appointment(db, appointment_id):
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
