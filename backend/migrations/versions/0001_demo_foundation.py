"""Create organizational demo foundation.

Revision ID: 0001_demo_foundation
Revises:
Create Date: 2026-05-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_demo_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "org_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("org_units.id"), nullable=True),
        sa.Column("path", sa.String(length=1000), nullable=False, unique=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "staffing_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_unit_id", sa.Integer(), sa.ForeignKey("org_units.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("approved_fte", sa.Float(), nullable=False),
        sa.Column("reported_occupied_fte", sa.Float(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_employee_id", sa.String(length=100), nullable=True, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("system_role", sa.String(length=32), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("staffing_line_id", sa.Integer(), sa.ForeignKey("staffing_lines.id"), nullable=False),
        sa.Column("manager_assignment_id", sa.Integer(), sa.ForeignKey("assignments.id")),
        sa.Column("fte", sa.Float(), nullable=False),
        sa.Column("assignment_role", sa.String(length=32), nullable=False),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("details_json", sa.String()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("assignments")
    op.drop_table("employees")
    op.drop_table("staffing_lines")
    op.drop_table("org_units")

