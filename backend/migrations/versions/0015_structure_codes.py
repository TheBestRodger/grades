"""Add imported department and position codes.

Revision ID: 0015_structure_codes
Revises: 0014_employee_login_timestamps
Create Date: 2026-06-03
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0015_structure_codes"
down_revision: str | None = "0014_employee_login_timestamps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("org_units", sa.Column("department_code", sa.String(length=80), nullable=True))
    op.add_column("staffing_lines", sa.Column("position_code", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("staffing_lines", "position_code")
    op.drop_column("org_units", "department_code")
