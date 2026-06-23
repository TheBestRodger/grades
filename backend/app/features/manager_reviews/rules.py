from __future__ import annotations

MANAGER_REVIEW_OPEN_STATUSES = {"under_review", "returned_by_hr"}


def can_take_for_review(workflow_status: str, has_revision: bool) -> bool:
    return workflow_status == "submitted" and has_revision


def can_manager_decide(workflow_status: str, has_revision: bool) -> bool:
    return workflow_status in MANAGER_REVIEW_OPEN_STATUSES and has_revision
