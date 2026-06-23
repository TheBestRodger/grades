from __future__ import annotations


def can_hr_decide(workflow_status: str, has_revision: bool) -> bool:
    return workflow_status == "manager_verified" and has_revision
