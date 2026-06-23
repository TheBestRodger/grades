"""Use email as login for employees.

Revision ID: 0018_email_login
Revises: 0017_employee_hr_flag
Create Date: 2026-06-09
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0018_email_login"
down_revision: str | None = "0017_employee_hr_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE employees SET username = lower(email) WHERE email IS NOT NULL"))

    with op.batch_alter_table("employees") as batch_op:
        batch_op.alter_column(
            "username",
            existing_type=sa.String(length=100),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.alter_column(
            "username",
            existing_type=sa.String(length=255),
            type_=sa.String(length=100),
            existing_nullable=True,
        )
