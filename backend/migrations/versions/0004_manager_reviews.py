"""Add manager profile review event history.

Revision ID: 0004_manager_reviews
Revises: 0003_profiles
Create Date: 2026-05-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_manager_reviews"
down_revision: str | None = "0003_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profile_review_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_profile_id", sa.Integer(), sa.ForeignKey("employee_profiles.id"), nullable=False),
        sa.Column("revision_id", sa.Integer(), sa.ForeignKey("profile_revisions.id"), nullable=False),
        sa.Column("actor_employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("profile_review_events")
