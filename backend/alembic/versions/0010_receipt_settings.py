"""recibo: nome completo, CPF, consultorios (cidade/endereco) e numeracao

Revision ID: 0010_receipt
Revises: 0009_guardians
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_receipt"
down_revision = "0009_guardians"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.add_column(sa.Column("legal_name", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("cpf", sa.String(length=20), nullable=True))
        # Lista JSON de consultorios: [{"city", "address", "phone"}]
        batch.add_column(sa.Column("offices", sa.Text(), nullable=True))
        batch.add_column(sa.Column("receipt_next", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.drop_column("receipt_next")
        batch.drop_column("offices")
        batch.drop_column("cpf")
        batch.drop_column("legal_name")
