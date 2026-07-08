"""Schemas Pydantic (contratos da API)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------- Settings ----------
class SettingsIn(BaseModel):
    professional_name: str = ""
    professional_title: str = "Psicóloga"
    crp: str = ""
    logo_includes_info: bool = False


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    professional_name: str
    professional_title: str
    crp: str
    logo_path: str | None = None
    logo_includes_info: bool = False
    has_password: bool = False
    recovery_email: str | None = None
    has_smtp: bool = False
    created_at: str
    updated_at: str


class RecoveryIn(BaseModel):
    """Configuracao de recuperacao de senha por e-mail (opcional)."""

    recovery_email: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None


class ResetRequestIn(BaseModel):
    email: str


class ResetConfirmIn(BaseModel):
    code: str
    new_password: str


# ---------- Appointment (agenda) ----------
class AppointmentIn(BaseModel):
    patient_id: str | None = None
    title: str = ""
    start_at: str            # 'YYYY-MM-DDTHH:MM'
    end_at: str
    status: str = "agendada"
    modality: str | None = None
    color: str | None = None
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    patient_id: str | None = None
    title: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    status: str | None = None
    modality: str | None = None
    color: str | None = None
    notes: str | None = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str | None = None
    patient_name: str = ""
    title: str
    start_at: str
    end_at: str
    status: str
    modality: str | None = None
    color: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


# ---------- Patient ----------
class PatientIn(BaseModel):
    name: str = ""
    birth_date: str | None = None
    sex: str | None = None
    phones: str | None = None
    notes: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    birth_date: str | None = None
    sex: str | None = None
    phones: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str
    age: str = ""
    anamneses_count: int = 0


# ---------- Anamnesis ----------
class AnamnesisCreate(BaseModel):
    patient_id: str
    data: dict = Field(default_factory=dict)


class AnamnesisUpdate(BaseModel):
    # Todos opcionais: autosave envia patches parciais.
    data: dict | None = None
    status: str | None = None


class AnamnesisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    form_version: str
    status: str
    data: dict
    created_at: str
    updated_at: str


class AnamnesisSummary(BaseModel):
    """Item de lista (sem o corpo completo dos dados)."""

    id: str
    patient_id: str
    patient_name: str = ""
    form_version: str
    status: str
    created_at: str
    updated_at: str
    missing_total: int = 0
