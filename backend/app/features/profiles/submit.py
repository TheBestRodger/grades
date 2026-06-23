from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import Employee, ProfileDraft, ProfileRevision
from .schemas import ProfileAnswersRequest
from ..organization.service import resolve_manager_assignment_for_line
from .audit import audit_profile_event
from .draft import answers_from_request, get_owned_profile
from .questionnaire import get_effective_profile_questions
from .rules import (
    EDITABLE_STATUSES,
    PROFILE_QUESTIONS,
    ProfileOperationError,
    _is_answer_filled,
    _validate_answers,
    assistant_payload,
    ensure_known_answer_keys,
)
from .serializers import serialize_profile
from .time import now
from ..notifications.service import create_notification, notify_hr_users


def submit_profile(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ProfileAnswersRequest,
    assistant_mode: str,
) -> dict[str, object]:
    profile = get_owned_profile(session, actor, profile_id)
    if profile.workflow_status not in EDITABLE_STATUSES:
        raise ProfileOperationError("Профиль заблокирован для отправки.", 409)
    ensure_known_answer_keys(request)
    answers = answers_from_request(profile, request)
    _validate_answers(answers)
    _ensure_all_required_answers_filled(answers)

    current_time = now()
    manager_assignment = _resolve_profile_route(session, profile, actor)
    revision = _create_revision(session, profile, request, answers, assistant_mode, current_time)
    direct_hr_route = manager_assignment is None
    profile.workflow_status = "manager_verified" if direct_hr_route else "submitted"
    profile.progress_percent = 100
    profile.last_activity_at = current_time
    if profile.started_at is None:
        profile.started_at = current_time
    audit_profile_event(
        session,
        actor,
        "profile.submitted",
        profile.id,
        {
            "revision_no": revision.revision_no,
            "assistant_mode": revision.assistant_mode,
            "assistance_level": revision.assistance_level,
            "ai_checked_questions": request.ai_checked_questions,
            "ai_ignored_questions": request.ai_ignored_questions,
            "direct_hr_route": direct_hr_route,
        },
    )
    if manager_assignment is not None:
        create_notification(
            session,
            recipient_id=manager_assignment.employee_id,
            notification_type="profile_submitted",
            title="Профиль ожидает проверки",
            message=f"Сотрудник {actor.full_name} отправил профиль на проверку.",
            target_section="manager-reviews",
            entity_type="employee_profile",
            entity_id=profile.id,
            dedupe_key=f"profile-submitted:{profile.id}:{revision.revision_no}",
        )
    else:
        notify_hr_users(
            session,
            is_demo=profile.participant.campaign.is_demo,
            notification_type="profile_submitted",
            title="Профиль ожидает проверки HR",
            message=f"Сотрудник {actor.full_name} отправил профиль напрямую в HR.",
            target_section="hr-reviews",
            entity_type="employee_profile",
            entity_id=profile.id,
            dedupe_key=f"profile-submitted-hr:{profile.id}:{revision.revision_no}",
            exclude_employee_id=actor.id,
        )
    session.flush()
    return serialize_profile(profile, get_effective_profile_questions(session))


def _ensure_all_required_answers_filled(answers: dict[str, str]) -> None:
    missing = [
        question["title"]
        for question in PROFILE_QUESTIONS
        if not _is_answer_filled(question, answers.get(question["key"], ""))
    ]
    if missing:
        raise ProfileOperationError(
            "Перед отправкой заполните разделы: " + ", ".join(missing) + ".",
            422,
        )


def _resolve_profile_route(session: Session, profile, actor: Employee):
    assignment = profile.participant.assignment
    if assignment.manager is not None:
        return assignment.manager
    resolved_manager = resolve_manager_assignment_for_line(
        session,
        assignment.staffing_line,
        exclude_employee_id=actor.id,
    )
    if assignment.manager_assignment_id is None and resolved_manager is not None:
        assignment.manager_assignment_id = resolved_manager.id
        assignment.manager = resolved_manager
    return resolved_manager


def _create_revision(
    session: Session,
    profile,
    request: ProfileAnswersRequest,
    answers: dict[str, str],
    assistant_mode: str,
    current_time,
) -> ProfileRevision:
    revision_assistant_mode, assistance_level, assisted_sections_json = assistant_payload(
        request,
        assistant_mode,
    )
    _upsert_draft(profile, answers, assisted_sections_json, current_time)
    next_number = max((revision.revision_no for revision in profile.revisions), default=0) + 1
    prior = max(profile.revisions, key=lambda item: item.revision_no, default=None)
    revision = ProfileRevision(
        profile=profile,
        revision_no=next_number,
        based_on_revision_id=prior.id if prior else None,
        answers_json=json.dumps(answers, ensure_ascii=False),
        submitted_at=current_time,
        assistant_mode=revision_assistant_mode,
        assistance_level=assistance_level,
        assisted_sections_json=assisted_sections_json,
        ai_check_status="not_run",
    )
    session.add(revision)
    return revision


def _upsert_draft(profile, answers: dict[str, str], assisted_sections_json: str, current_time) -> None:
    if profile.draft is None:
        profile.draft = ProfileDraft(
            answers_json=json.dumps(answers, ensure_ascii=False),
            ai_usage_json=assisted_sections_json,
            updated_at=current_time,
        )
        return
    profile.draft.answers_json = json.dumps(answers, ensure_ascii=False)
    profile.draft.ai_usage_json = assisted_sections_json
    profile.draft.updated_at = current_time
