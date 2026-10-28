"""responsaveis + valor da sessao + vinculo cobranca-sessao

Revision ID: 0009_guardians
Revises: 0008_evolution
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_guardians"
down_revision = "0008_evolution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guardians",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.String(length=36), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("kinship", sa.String(length=60), nullable=True),
        sa.Column("phone", sa.String(length=60), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("cpf", sa.String(length=20), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_guardians_patient", "guardians", ["patient_id"])

    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("session_price_cents", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("finance_entries") as batch:
        batch.add_column(sa.Column("appointment_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("finance_entries") as batch:
        batch.drop_column("appointment_id")
    with op.batch_alter_table("patients") as batch:
        batch.drop_column("session_price_cents")
    op.drop_index("ix_guardians_patient", table_name="guardians")
    op.drop_table("guardians")
