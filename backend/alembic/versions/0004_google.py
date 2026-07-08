"""integracao com a Agenda Google (config em settings)

Revision ID: 0004_google
Revises: 0003_agenda
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_google"
down_revision = "0003_agenda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        batch.add_column(sa.Column("google_client_id", sa.String(length=300), nullable=True))
        batch.add_column(sa.Column("google_client_secret", sa.String(length=300), nullable=True))
        batch.add_column(sa.Column("google_calendar_id", sa.String(length=200),
                                   nullable=False, server_default="primary"))
        batch.add_column(sa.Column("google_timezone", sa.String(length=60),
                                   nullable=False, server_default="America/Sao_Paulo"))


def downgrade() -> None:
    with op.batch_alter_table("settings") as batch:
        for col in ("google_timezone", "google_calendar_id", "google_client_secret",
                    "google_client_id"):
            batch.drop_column(col)
