"""Add personal notifications.

Revision ID: 0020_notifications
Revises: 0019_runtime_indexes
Create Date: 2026-06-19
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0020_notifications"
down_revision: str | None = "0019_runtime_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipient_employee_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("target_section", sa.String(length=80), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["recipient_employee_id"],
            ["employees.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["recipient_employee_id", "read_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_recipient_read_created",
        table_name="notifications",
    )
    op.drop_table("notifications")
