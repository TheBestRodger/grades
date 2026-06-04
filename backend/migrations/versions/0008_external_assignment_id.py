"""Add source identifier for imported assignments.

Revision ID: 0008_external_assignment_id
Revises: 0007_campaign_wave_unit_selections
Create Date: 2026-05-27
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_external_assignment_id"
down_revision: str | None = "0007_campaign_wave_unit_selections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assignments", sa.Column("external_assignment_id", sa.String(length=100)))
    op.create_index(
        "ix_assignments_external_assignment_id",
        "assignments",
        ["external_assignment_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_assignments_external_assignment_id", table_name="assignments")
    op.drop_column("assignments", "external_assignment_id")
