from __future__ import annotations

import json

from ...models import EmployeeProfile, ProfileDraft, ProfileRevision
from .routing import route_current, route_path, route_reason
from .rules import EDITABLE_STATUSES, LOCKED_PREFILLED_QUESTION_KEYS, _prefilled_section_one_answers
from .time import now


def answers_from_draft(profile: EmployeeProfile) -> dict[str, str]:
    if profile.draft is None:
        return {}
    return json.loads(profile.draft.answers_json)


def answers_for_profile(profile: EmployeeProfile) -> dict[str, str]:
    answers = _prefilled_section_one_answers(profile)
    answers.update(
        {
            key: value
            for key, value in answers_from_draft(profile).items()
            if key not in LOCKED_PREFILLED_QUESTION_KEYS
        }
    )
    return with_system_answers(answers)


def with_system_answers(answers: dict[str, str]) -> dict[str, str]:
    next_answers = dict(answers)
    next_answers["completion_date"] = now().strftime("%d.%m.%Y")
    return next_answers


def serialize_profile(
    profile: EmployeeProfile,
    questions: list[dict[str, object]],
) -> dict[str, object]:
    participant = profile.participant
    assignment = participant.assignment
    line = assignment.staffing_line
    revisions = sorted(profile.revisions, key=lambda item: item.revision_no, reverse=True)
    return {
        "id": profile.id,
        "campaign_id": participant.campaign_id,
        "campaign_name": participant.campaign.name,
        "assignment_id": participant.assignment_id,
        "position_title": line.title,
        "unit_name": line.org_unit.name,
        "workflow_status": profile.workflow_status,
        "progress_percent": profile.progress_percent,
        "route_path": route_path(profile),
        "route_current": route_current(profile),
        "route_reason": route_reason(profile),
        "answers": answers_for_profile(profile),
        "draft_assisted_sections": draft_assisted_sections(profile.draft),
        "can_edit": profile.workflow_status in EDITABLE_STATUSES,
        "questions": questions,
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
        "revisions": [
            {
                "id": revision.id,
                "revision_no": revision.revision_no,
                "submitted_at": revision.submitted_at.isoformat(),
                "assistant_mode": revision.assistant_mode,
                "assistance_level": revision.assistance_level,
                "assisted_sections": assisted_sections(revision),
                "answers": json.loads(revision.answers_json),
            }
            for revision in revisions
        ],
    }


def assisted_sections(revision: ProfileRevision) -> dict[str, object]:
    return assisted_sections_from_json(revision.assisted_sections_json)


def draft_assisted_sections(draft: ProfileDraft | None) -> dict[str, object]:
    return assisted_sections_from_json(draft.ai_usage_json if draft is not None else "{}")


def assisted_sections_from_json(raw: str) -> dict[str, object]:
    empty = {
        "checked_questions": [],
        "ignored_questions": [],
        "without_ai_questions": [],
        "answer_statuses": {},
    }
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return empty
    if isinstance(payload, dict):
        return {
            "checked_questions": payload.get("checked_questions", []),
            "ignored_questions": payload.get("ignored_questions", []),
            "without_ai_questions": payload.get("without_ai_questions", []),
            "answer_statuses": payload.get("answer_statuses", {}),
        }
    if isinstance(payload, list):
        return {**empty, "checked_questions": payload}
    return empty


_answers_from_draft = answers_from_draft
_answers_for_profile = answers_for_profile
_with_system_answers = with_system_answers
_serialize_profile = serialize_profile
_assisted_sections = assisted_sections
_draft_assisted_sections = draft_assisted_sections
_assisted_sections_from_json = assisted_sections_from_json
