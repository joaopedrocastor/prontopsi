"""ficha de cliente: email/status + timeline + documentos

Revision ID: 0005_client
Revises: 0004_google
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_client"
down_revision = "0004_google"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("email", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=20), nullable=False,
                                   server_default="ativo"))

    op.create_table(
        "client_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.String(length=36),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_client_notes_patient_id", "client_notes", ["patient_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.String(length=36),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=400), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mime", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.String(length=30), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_documents_patient_id", "documents", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_patient_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_client_notes_patient_id", table_name="client_notes")
    op.drop_table("client_notes")
    with op.batch_alter_table("patients") as batch:
        batch.drop_column("status")
        batch.drop_column("email")
