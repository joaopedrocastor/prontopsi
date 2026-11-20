"""recibos emitidos (salvos para reabrir, editar e gerar o PDF de novo)

Revision ID: 0011_receipts
Revises: 0010_receipt
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_receipts"
down_revision = "0010_receipt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column("issued_on", sa.String(length=10), nullable=False),
        sa.Column("patient_id", sa.String(length=36), sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("patient_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("payer", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("payer_cpf", sa.String(length=20), nullable=True),
        sa.Column("payer_title", sa.String(length=5), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sessions", sa.Integer(), nullable=True),
        sa.Column("session_dates", sa.Text(), nullable=True),  # JSON ['YYYY-MM-DD']
        sa.Column("service", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_receipts_issued_on", "receipts", ["issued_on"])
    op.create_index("ix_receipts_patient", "receipts", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_receipts_patient", table_name="receipts")
    op.drop_index("ix_receipts_issued_on", table_name="receipts")
    op.drop_table("receipts")
