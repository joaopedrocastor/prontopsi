"""financeiro: tabela de lancamentos (receitas/despesas)

Revision ID: 0007_finance
Revises: 0006_drive
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_finance"
down_revision = "0006_drive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finance_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=10), nullable=False, server_default="receita"),
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("due_date", sa.String(length=10), nullable=False),
        sa.Column("paid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paid_date", sa.String(length=10), nullable=True),
        sa.Column("recurrence", sa.String(length=10), nullable=False, server_default="nenhuma"),
        sa.Column("patient_id", sa.String(length=36), sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_finance_due_date", "finance_entries", ["due_date"])
    op.create_index("ix_finance_kind", "finance_entries", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_finance_kind", table_name="finance_entries")
    op.drop_index("ix_finance_due_date", table_name="finance_entries")
    op.drop_table("finance_entries")
