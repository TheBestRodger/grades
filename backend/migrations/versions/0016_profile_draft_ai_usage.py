"""Store AI usage metadata for profile drafts.

Revision ID: 0016_profile_draft_ai_usage
Revises: 0015_structure_codes
Create Date: 2026-06-03
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_profile_draft_ai_usage"
down_revision: str | None = "0015_structure_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profile_drafts",
        sa.Column("ai_usage_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("profile_drafts", "ai_usage_json")
