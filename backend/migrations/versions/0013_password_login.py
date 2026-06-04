"""Add username/password login for pilot access.

Revision ID: 0013_password_login
Revises: 0012_questionnaire_answer_settings
Create Date: 2026-06-02
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0013_password_login"
down_revision: str | None = "0012_questionnaire_answer_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("username", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("password_hash", sa.String(length=255), nullable=True))

    connection = op.get_bind()
    employees = connection.execute(sa.text("SELECT id, email FROM employees ORDER BY id")).mappings().all()
    used: set[str] = set()
    for employee in employees:
        base = employee["email"].split("@", 1)[0].strip().lower() or f"user{employee['id']}"
        base = "".join(char if char.isalnum() or char in {"_", ".", "-"} else "." for char in base)
        username = base
        suffix = 2
        while username in used:
            username = f"{base}{suffix}"
            suffix += 1
        used.add(username)
        connection.execute(
            sa.text("UPDATE employees SET username = :username WHERE id = :id"),
            {"id": employee["id"], "username": username},
        )

    with op.batch_alter_table("employees") as batch_op:
        batch_op.create_unique_constraint("uq_employees_username", ["username"])


def downgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.drop_constraint("uq_employees_username", type_="unique")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("username")
