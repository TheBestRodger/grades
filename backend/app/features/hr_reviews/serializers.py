from __future__ import annotations

import json

from ...models import EmployeeProfile, ProfileRevision
from ..profiles.routing import route_current, route_path, route_reason


def latest_revision(profile: EmployeeProfile) -> ProfileRevision | None:
    return max(profile.revisions, key=lambda item: item.revision_no, default=None)


def assisted_sections(revision: ProfileRevision) -> dict[str, object]:
    try:
        payload = json.loads(revision.assisted_sections_json or "{}")
    except json.JSONDecodeError:
        return {"checked_questions": [], "ignored_questions": [], "without_ai_questions": []}
    if isinstance(payload, dict):
        return {
            "checked_questions": payload.get("checked_questions", []),
            "ignored_questions": payload.get("ignored_questions", []),
            "without_ai_questions": payload.get("without_ai_questions", []),
            "answer_statuses": payload.get("answer_statuses", {}),
        }
    if isinstance(payload, list):
        return {"checked_questions": payload, "ignored_questions": [], "without_ai_questions": []}
    return {"checked_questions": [], "ignored_questions": [], "without_ai_questions": []}


def serialize_review(
    profile: EmployeeProfile,
    questions: list[dict[str, object]],
) -> dict[str, object]:
    assignment = profile.participant.assignment
    latest = latest_revision(profile)
    return {
        "id": profile.id,
        "employee_name": assignment.employee.full_name,
        "position_title": assignment.staffing_line.title,
        "org_unit_id": assignment.staffing_line.org_unit_id,
        "unit_name": assignment.staffing_line.org_unit.name,
        "campaign_name": profile.participant.campaign.name,
        "workflow_status": profile.workflow_status,
        "progress_percent": profile.progress_percent,
        "route_path": route_path(profile),
        "route_current": route_current(profile),
        "route_reason": route_reason(profile),
        "questions": questions,
        "latest_revision": (
            {
                "id": latest.id,
                "revision_no": latest.revision_no,
                "submitted_at": latest.submitted_at.isoformat(),
                "assistant_mode": latest.assistant_mode,
                "assistance_level": latest.assistance_level,
                "assisted_sections": assisted_sections(latest),
                "answers": json.loads(latest.answers_json),
            }
            if latest
            else None
        ),
        "review_events": [
            {
                "id": event.id,
                "revision_no": event.revision.revision_no,
                "action": event.action,
                "comment": event.comment,
                "actor_name": event.actor.full_name,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in sorted(profile.review_events, key=lambda item: item.id, reverse=True)
        ],
        "can_decide": profile.workflow_status == "manager_verified" and latest is not None,
    }


_latest_revision = latest_revision
_assisted_sections = assisted_sections
_serialize = serialize_review
