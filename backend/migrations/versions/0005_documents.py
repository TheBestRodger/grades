"""Add document registry and target links.

Revision ID: 0005_documents
Revises: 0004_manager_reviews
Create Date: 2026-05-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_documents"
down_revision: str | None = "0004_manager_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_code", sa.String(length=80), nullable=False, unique=True),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("document_status", sa.String(length=32), nullable=False),
        sa.Column("source_file_path", sa.String(length=1000)),
        sa.Column("extracted_text_path", sa.String(length=1000)),
        sa.Column("content_text", sa.Text()),
        sa.Column("ocr_quality_status", sa.String(length=32), nullable=False),
        sa.Column("checksum", sa.String(length=128)),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "document_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("link_status", sa.String(length=32), nullable=False),
        sa.Column("confirmed_by_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("confirmed_at", sa.DateTime()),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("document_id", "target_type", "target_id", name="uq_document_target"),
    )


def downgrade() -> None:
    op.drop_table("document_links")
    op.drop_table("documents")
