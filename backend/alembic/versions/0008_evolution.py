"""agenda: evolucao clinica da sessao (prontuario)

Revision ID: 0008_evolution
Revises: 0007_finance
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_evolution"
down_revision = "0007_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("appointments") as batch:
        batch.add_column(sa.Column("evolution", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("appointments") as batch:
        batch.drop_column("evolution")
