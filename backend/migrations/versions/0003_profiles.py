"""Add employee profile drafts and submitted revisions.

Revision ID: 0003_profiles
Revises: 0002_campaigns
Create Date: 2026-05-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_profiles"
down_revision: str | None = "0002_campaigns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employee_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "campaign_participant_id",
            sa.Integer(),
            sa.ForeignKey("campaign_participants.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("workflow_status", sa.String(length=32), nullable=False),
        sa.Column("progress_percent", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("last_activity_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "profile_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "employee_profile_id",
            sa.Integer(),
            sa.ForeignKey("employee_profiles.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "profile_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_profile_id", sa.Integer(), sa.ForeignKey("employee_profiles.id"), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("based_on_revision_id", sa.Integer(), sa.ForeignKey("profile_revisions.id")),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("assistant_mode", sa.String(length=32), nullable=False),
        sa.Column("assistance_level", sa.String(length=32), nullable=False),
        sa.Column("assisted_sections_json", sa.Text(), nullable=False),
        sa.Column("ai_check_status", sa.String(length=32), nullable=False),
        sa.Column("locked_at", sa.DateTime()),
        sa.UniqueConstraint("employee_profile_id", "revision_no", name="uq_profile_revision_no"),
    )
    op.execute(
        sa.text(
            "INSERT INTO employee_profiles "
            "(campaign_participant_id, workflow_status, progress_percent) "
            "SELECT id, 'not_started', 0 FROM campaign_participants"
        )
    )


def downgrade() -> None:
    op.drop_table("profile_revisions")
    op.drop_table("profile_drafts")
    op.drop_table("employee_profiles")
