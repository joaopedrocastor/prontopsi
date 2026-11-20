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

    # Dados do recibo: nome completo e CPF da profissional, consultorios
    # (JSON: [{"city", "address", "phone"}] — a cidade escolhida no recibo
    # define o endereco do rodape) e o proximo numero de recibo.
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    offices: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_next: Mapped[int] = mapped_column(Integer, default=1)

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
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Situação do cliente: ativo | espera | alta | desativado | desistente
    status: Mapped[str] = mapped_column(String(20), default="ativo")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Valor padrao da sessao deste cliente, em centavos (0 = nao definido).
    # Usado na cobranca automatica quando a sessao e marcada como realizada.
    session_price_cents: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    guardians: Mapped[list["Guardian"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan",
        order_by="Guardian.is_primary.desc()",
    )
    anamneses: Mapped[list["Anamnesis"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="Anamnesis.created_at.desc()",
    )
    client_notes: Mapped[list["ClientNote"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan",
        order_by="ClientNote.date.desc()",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan",
        order_by="Document.created_at.desc()",
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
    # ID do PDF desta ficha no Google Drive (quando salvo lá) — evita duplicar.
    google_drive_file_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

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
    # Evolucao clinica da sessao (prontuario). Preenchida apos a sessao.
    evolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient | None"] = relationship()


class Receipt(Base):
    """Recibo emitido. Guardado para reabrir, corrigir e gerar o PDF de novo
    (mantendo o mesmo número). A numeração é contínua e automática."""

    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    issued_on: Mapped[str] = mapped_column(String(10))  # data do recibo 'YYYY-MM-DD'
    patient_id: Mapped[str | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    patient_name: Mapped[str] = mapped_column(String(200), default="")
    payer: Mapped[str] = mapped_column(String(200), default="")
    payer_cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payer_title: Mapped[str | None] = mapped_column(String(5), nullable=True)  # 'Sr.' | 'Sra.'
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    sessions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_dates: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    service: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(100), default="")

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient | None"] = relationship()


class FinanceEntry(Base):
    """Lancamento financeiro (receita ou despesa).

    Valor guardado em centavos (inteiro) para evitar erro de ponto flutuante.
    `due_date` e a data de competencia/vencimento (YYYY-MM-DD). Pode estar
    opcionalmente ligado a um paciente (ex.: cobranca de sessao).
    """

    __tablename__ = "finance_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    kind: Mapped[str] = mapped_column(String(10), default="receita")  # 'receita' | 'despesa'
    description: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[str] = mapped_column(String(60), default="")  # tag livre
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    due_date: Mapped[str] = mapped_column(String(10))  # ISO 'YYYY-MM-DD'
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # 'nenhuma' | 'semanal' | 'mensal' | 'anual'
    recurrence: Mapped[str] = mapped_column(String(10), default="nenhuma")
    patient_id: Mapped[str | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    # Sessao que originou esta cobranca (evita cobrar a mesma sessao duas vezes).
    appointment_id: Mapped[str | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient | None"] = relationship()


class Guardian(Base):
    """Responsavel pelo cliente (mae/pai/avo/escola). Importante no infantil."""

    __tablename__ = "guardians"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), default="")
    kinship: Mapped[str | None] = mapped_column(String(60), nullable=True)  # parentesco
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient"] = relationship(back_populates="guardians")


class ClientNote(Base):
    """Anotação da timeline do cliente (histórico clínico em ordem de data)."""

    __tablename__ = "client_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    date: Mapped[str] = mapped_column(String(10))  # ISO 'YYYY-MM-DD'
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient"] = relationship(back_populates="client_notes")


class Document(Base):
    """Documento anexado ao cliente. O arquivo fica em data/documents/."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))          # nome original
    stored_path: Mapped[str] = mapped_column(String(400))       # relativo ao diretório de dados
    size: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[str] = mapped_column(String(30), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(30), default=now_iso, onupdate=now_iso)

    patient: Mapped["Patient"] = relationship(back_populates="documents")
