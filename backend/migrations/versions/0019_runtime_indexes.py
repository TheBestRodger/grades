"""Add runtime indexes for pilot database.

Revision ID: 0019_runtime_indexes
Revises: 0018_email_login
Create Date: 2026-06-16
"""

from typing import Sequence

from alembic import op


revision: str = "0019_runtime_indexes"
down_revision: str | None = "0018_email_login"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_auth_login_tokens_employee_expires",
        "auth_login_tokens",
        ["employee_id", "expires_at"],
    )
    op.create_index(
        "ix_auth_sessions_employee_expires",
        "auth_sessions",
        ["employee_id", "expires_at"],
    )
    op.create_index(
        "ix_campaigns_demo_status_id",
        "campaigns",
        ["is_demo", "status", "id"],
    )
    op.create_index(
        "ix_campaign_waves_campaign_status",
        "campaign_waves",
        ["campaign_id", "status"],
    )
    op.create_index(
        "ix_campaign_participants_campaign_status",
        "campaign_participants",
        ["campaign_id", "participation_status", "expected_to_submit"],
    )
    op.create_index(
        "ix_campaign_participants_assignment_status",
        "campaign_participants",
        ["assignment_id", "participation_status", "expected_to_submit"],
    )
    op.create_index(
        "ix_employee_profiles_workflow_status",
        "employee_profiles",
        ["workflow_status"],
    )
    op.create_index(
        "ix_documents_demo_type_code",
        "documents",
        ["is_demo", "document_type", "document_code"],
    )
    op.create_index(
        "ix_documents_demo_checksum",
        "documents",
        ["is_demo", "checksum"],
    )
    op.create_index(
        "ix_document_links_target_demo",
        "document_links",
        ["target_type", "target_id", "is_demo"],
    )
    op.create_index(
        "ix_document_links_document_status",
        "document_links",
        ["document_id", "link_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_links_document_status", table_name="document_links")
    op.drop_index("ix_document_links_target_demo", table_name="document_links")
    op.drop_index("ix_documents_demo_checksum", table_name="documents")
    op.drop_index("ix_documents_demo_type_code", table_name="documents")
    op.drop_index("ix_employee_profiles_workflow_status", table_name="employee_profiles")
    op.drop_index(
        "ix_campaign_participants_assignment_status",
        table_name="campaign_participants",
    )
    op.drop_index(
        "ix_campaign_participants_campaign_status",
        table_name="campaign_participants",
    )
    op.drop_index("ix_campaign_waves_campaign_status", table_name="campaign_waves")
    op.drop_index("ix_campaigns_demo_status_id", table_name="campaigns")
    op.drop_index("ix_auth_sessions_employee_expires", table_name="auth_sessions")
    op.drop_index(
        "ix_auth_login_tokens_employee_expires",
        table_name="auth_login_tokens",
    )
