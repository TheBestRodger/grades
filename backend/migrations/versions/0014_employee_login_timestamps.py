"""Track first and last password login timestamps.

Revision ID: 0014_employee_login_timestamps
Revises: 0013_password_login
Create Date: 2026-06-02
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014_employee_login_timestamps"
down_revision: str | None = "0013_password_login"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("first_login_at", sa.DateTime(), nullable=True))
    op.add_column("employees", sa.Column("last_login_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "last_login_at")
    op.drop_column("employees", "first_login_at")
