from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import Employee, EmployeeProfile, ProfileDraft
from .schemas import ProfileAnswersRequest
from .audit import audit_profile_event
from .questionnaire import get_effective_profile_questions
from .repository import load_owned_profile
from .rules import (
    EDITABLE_STATUSES,
    LOCKED_PREFILLED_QUESTION_KEYS,
    ProfileOperationError,
    _prefilled_section_one_answers,
    _progress,
    _validate_answers,
    assistant_payload,
    ensure_known_answer_keys,
)
from .serializers import serialize_profile
from .time import now


def save_draft(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ProfileAnswersRequest,
    assistant_mode: str,
) -> dict[str, object]:
    profile = get_owned_profile(session, actor, profile_id)
    if profile.workflow_status not in EDITABLE_STATUSES:
        raise ProfileOperationError("Профиль заблокирован для редактирования.", 409)
    ensure_known_answer_keys(request)
    answers = answers_from_request(profile, request)
    _validate_answers(answers)

    current_time = now()
    assistant = assistant_payload(request, assistant_mode)
    if profile.draft is None:
        profile.draft = ProfileDraft(
            answers_json=json.dumps(answers, ensure_ascii=False),
            ai_usage_json=assistant[2],
            updated_at=current_time,
        )
    else:
        profile.draft.answers_json = json.dumps(answers, ensure_ascii=False)
        profile.draft.ai_usage_json = assistant[2]
        profile.draft.updated_at = current_time
    if profile.started_at is None:
        profile.started_at = current_time
    profile.last_activity_at = current_time
    profile.progress_percent = _progress(answers)
    profile.workflow_status = "draft"
    audit_profile_event(
        session,
        actor,
        "profile.draft_saved",
        profile.id,
        {
            "progress_percent": profile.progress_percent,
            "assistant_mode": assistant[0],
            "ai_checked_questions": request.ai_checked_questions,
            "ai_ignored_questions": request.ai_ignored_questions,
            "ai_without_ai_questions": request.ai_without_ai_questions,
        },
    )
    session.flush()
    return serialize_profile(profile, get_effective_profile_questions(session))


def get_owned_profile(session: Session, actor: Employee, profile_id: int) -> EmployeeProfile:
    profile = load_owned_profile(session, actor, profile_id)
    if profile is None:
        raise ProfileOperationError("Профиль не найден или недоступен.", 404)
    return profile


def answers_from_request(profile: EmployeeProfile, request: ProfileAnswersRequest) -> dict[str, str]:
    answers = {key: request.answers.get(key, "") for key in _question_keys()}
    prefilled = _prefilled_section_one_answers(profile)
    for key in LOCKED_PREFILLED_QUESTION_KEYS:
        answers[key] = prefilled.get(key, "")
    answers["completion_date"] = now().strftime("%d.%m.%Y")
    return answers


def _question_keys() -> set[str]:
    from .rules import QUESTION_KEYS

    return QUESTION_KEYS


_answers_from_request = answers_from_request
_get_owned_profile = get_owned_profile
