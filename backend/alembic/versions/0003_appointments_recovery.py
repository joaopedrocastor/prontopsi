"""agenda (appointments) + recuperacao de senha por e-mail

Revision ID: 0003_agenda
Revises: 0002_logo_info
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_agenda"
down_revision = "0002_logo_info"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.add_column(sa.Column("recovery_email", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("smtp_host", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("smtp_port", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("smtp_user", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("smtp_password", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("reset_code_hash", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("reset_expires", sa.String(length=30), nullable=True))

    op.create_table(
        "appointments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.String(length=36),
                  sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("start_at", sa.String(length=20), nullable=False),
        sa.Column("end_at", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="agendada"),
        sa.Column("modality", sa.String(length=20), nullable=True),
        sa.Column("color", sa.String(length=9), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("google_event_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_appointments_start_at", "appointments", ["start_at"])
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_appointments_patient_id", table_name="appointments")
    op.drop_index("ix_appointments_start_at", table_name="appointments")
    op.drop_table("appointments")
    with op.batch_alter_table("settings") as batch:
        for col in ("reset_expires", "reset_code_hash", "smtp_password", "smtp_user",
                    "smtp_port", "smtp_host", "recovery_email"):
            batch.drop_column(col)
