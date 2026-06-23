"""Restore direct-to-HR profiles returned for revision.

Revision ID: 0021_restore_direct_hr_returns
Revises: 0020_notifications
Create Date: 2026-06-19
"""

from typing import Sequence

from alembic import op


revision: str = "0021_restore_direct_hr_returns"
down_revision: str | None = "0020_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE employee_profiles AS profile
        SET workflow_status = 'returned_for_revision'
        FROM campaign_participants AS participant
        JOIN assignments AS assignment
          ON assignment.id = participant.assignment_id
        WHERE profile.campaign_participant_id = participant.id
          AND profile.workflow_status = 'returned_by_hr'
          AND assignment.manager_assignment_id IS NULL
        """
    )


def downgrade() -> None:
    # This is a data repair. Reverting it would recreate an invalid locked state.
    pass
