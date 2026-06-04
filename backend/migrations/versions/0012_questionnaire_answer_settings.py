"""Add questionnaire answer settings.

Revision ID: 0012_questionnaire_answer_settings
Revises: 0011_ai_clarity_settings
Create Date: 2026-05-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012_questionnaire_answer_settings"
down_revision: str | None = "0011_ai_clarity_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questionnaire_question_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_key", sa.String(length=100), nullable=False),
        sa.Column("ai_check_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("good_example", sa.Text(), nullable=True),
        sa.Column("bad_example", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["updated_by_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_key"),
    )


def downgrade() -> None:
    op.drop_table("questionnaire_question_settings")
