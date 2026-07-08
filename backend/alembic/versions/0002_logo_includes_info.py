"""settings.logo_includes_info

Revision ID: 0002_logo_info
Revises: 0001_initial
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_logo_info"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.add_column(sa.Column("logo_includes_info", sa.Boolean(), nullable=False,
                                   server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.drop_column("logo_includes_info")
