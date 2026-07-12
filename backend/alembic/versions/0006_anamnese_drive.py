"""anamnese: id do PDF no Google Drive

Revision ID: 0006_drive
Revises: 0005_client
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_drive"
down_revision = "0005_client"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("anamneses") as batch:
        batch.add_column(sa.Column("google_drive_file_id", sa.String(length=120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("anamneses") as batch:
        batch.drop_column("google_drive_file_id")
