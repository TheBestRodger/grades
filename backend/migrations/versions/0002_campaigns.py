"""Add campaigns and campaign participants.

Revision ID: 0002_campaigns
Revises: 0001_demo_foundation
Create Date: 2026-05-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_campaigns"
down_revision: str | None = "0001_demo_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_at", sa.Date()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "campaign_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), nullable=False),
        sa.Column("participation_status", sa.String(length=32), nullable=False),
        sa.Column("expected_to_submit", sa.Boolean(), nullable=False),
        sa.Column("included_by_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("included_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("campaign_id", "assignment_id", name="uq_campaign_assignment"),
    )


def downgrade() -> None:
    op.drop_table("campaign_participants")
    op.drop_table("campaigns")
