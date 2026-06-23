"""Add additive HR permission flag to employees.

Revision ID: 0017_employee_hr_flag
Revises: 0016_profile_draft_ai_usage
Create Date: 2026-06-09
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0017_employee_hr_flag"
down_revision: str | None = "0016_profile_draft_ai_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("is_hr", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE employees SET is_hr = TRUE WHERE system_role = 'hr'")


def downgrade() -> None:
    op.drop_column("employees", "is_hr")
