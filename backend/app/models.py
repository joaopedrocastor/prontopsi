"""Modelos ORM (camada de banco).

Preparado para a nuvem:
  - Chaves primarias em UUID (texto), nunca autoincremento.
  - Auditoria (created_at / updated_at) em ISO 8601 UTC em todos os registros.
  - Ficha guarda `form_version` para abrir corretamente mesmo se o formulario
    evoluir, e o conteudo em JSON (portavel SQLite -> PostgreSQL).
"""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils import new_uuid, now_iso


class Settings(Base):
    """Configuracao do consultorio (linha unica): identidade visual da ficha."""

    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    professional_name: Mapped[str] = mapped_column(String(200), default="")
    professional_title: Mapped[str] = mapped_column(String(100), default="Psicóloga")
    crp: Mapped[str] = mapped_column(String(50), default="")
    # Caminho RELATIVO ao diretorio de dados (ex.: "assets/logo.png"),
    # facil de mover para um storage na nuvem depois.
    logo_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Quando a logo enviada ja contem nome/titulo/CRP (lockup completo),
    # nao repetimos esse texto ao lado — apenas mostramos a logo maior.
    logo_includes_info: Mapped[bool] = mapped_column(Boolean, default=False)
    # Senha simples opcional de abertura (hash). Nulo = sem senha.
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Recuperacao de senha por e-mail (opcional).
    recovery_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Servidor SMTP opcional para enviar o codigo de recuperacao.
    smtp_host: Mapped[str | None] = mapped_column(String(200), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_user: Mapped[str | None] = mapped_column(String(200), nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Codigo de redefinicao em andamento (hash + validade ISO).
    reset_code_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reset_expires: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Integracao com a Agenda Google (opcional). O token OAuth fica em arquivo
    # no diretorio de dados (google_token.json); aqui guardamos so a config.
    google_client_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    google_client_secret: Mapped[str | None] = mapped_column(String(300), nullable=True)
    google_calendar_id: Mapped[str] = mapped_column(String(200), default="primary")
    google_timezone: Mapped[str] = mapped_column(String(60), default="America/Sao_Paulo")

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)


class Patient(Base):
    """Paciente (crianca)."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), default="")
    birth_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO 'YYYY-MM-DD'
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True)  # 'F' | 'M'
    phones: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    anamneses: Mapped[list["Anamnesis"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="Anamnesis.created_at.desc()",
    )


class Anamnesis(Base):
    """Ficha de anamnese. Conteudo dos campos guardado em JSON versionado."""

    __tablename__ = "anamneses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))

    form_version: Mapped[str] = mapped_column(String(20), default="1")
    status: Mapped[str] = mapped_column(String(20), default="rascunho")  # 'rascunho' | 'concluida'
    # Dicionario {chave_do_campo: valor} conforme form_schema.
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient"] = relationship(back_populates="anamneses")


class Appointment(Base):
    """Agendamento de consulta/sessao na agenda.

    Datas de inicio/fim guardadas como ISO local 'YYYY-MM-DDTHH:MM' (horario de
    parede da agenda). `google_event_id` reservado para a futura sincronizacao
    com a Agenda Google.
    """

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # Paciente opcional: permite eventos avulsos (palestra, bloqueio, etc.).
    patient_id: Mapped[str | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), default="")
    start_at: Mapped[str] = mapped_column(String(20))  # 'YYYY-MM-DDTHH:MM'
    end_at: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="agendada")
    # 'agendada' | 'confirmada' | 'realizada' | 'cancelada' | 'faltou'
    modality: Mapped[str | None] = mapped_column(String(20), nullable=True)  # presencial|online
    color: Mapped[str | None] = mapped_column(String(9), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient | None"] = relationship()
