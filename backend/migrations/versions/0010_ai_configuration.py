"""Add configurable AI mode settings.

Revision ID: 0010_ai_configuration
Revises: 0009_auth_sessions
Create Date: 2026-05-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010_ai_configuration"
down_revision: str | None = "0009_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=500)),
        sa.Column("model_name", sa.String(length=255)),
        sa.Column("api_token", sa.String(length=1000)),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_configurations")
