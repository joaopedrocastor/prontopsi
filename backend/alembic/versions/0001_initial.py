"""schema inicial: settings, patients, anamneses

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("professional_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("professional_title", sa.String(length=100), nullable=False,
                  server_default="Psicóloga"),
        sa.Column("crp", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("logo_path", sa.String(length=300), nullable=True),
        sa.Column("password_hash", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )

    op.create_table(
        "patients",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("birth_date", sa.String(length=10), nullable=True),
        sa.Column("sex", sa.String(length=1), nullable=True),
        sa.Column("phones", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_patients_name", "patients", ["name"])

    op.create_table(
        "anamneses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.String(length=36),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_version", sa.String(length=20), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="rascunho"),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_anamneses_patient_id", "anamneses", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_anamneses_patient_id", table_name="anamneses")
    op.drop_table("anamneses")
    op.drop_index("ix_patients_name", table_name="patients")
    op.drop_table("patients")
    op.drop_table("settings")
