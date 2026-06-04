"""Add AI interviewer clarity settings.

Revision ID: 0011_ai_clarity_settings
Revises: 0010_ai_configuration
Create Date: 2026-05-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011_ai_clarity_settings"
down_revision: str | None = "0010_ai_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_configurations",
        sa.Column("clarity_threshold", sa.Integer(), nullable=False, server_default="70"),
    )
    op.add_column(
        "ai_configurations",
        sa.Column("followup_strictness", sa.String(length=32), nullable=False, server_default="balanced"),
    )


def downgrade() -> None:
    op.drop_column("ai_configurations", "followup_strictness")
    op.drop_column("ai_configurations", "clarity_threshold")
