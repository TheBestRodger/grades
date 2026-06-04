from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Assignment,
    AuditEvent,
    Campaign,
    CampaignParticipant,
    Employee,
    EmployeeProfile,
    OrgUnit,
    ProfileReviewEvent,
    ProfileRevision,
    StaffingLine,
)
from .organization import _unit_descendants, _visible_unit_ids
from .profile_operations import get_effective_profile_questions
from .schemas import BulkReviewReturnRequest, ReviewReturnRequest, ReviewVerifyRequest


class ReviewOperationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _audit(
    session: Session,
    actor: Employee,
    action: str,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type="employee_profile",
            entity_id=str(profile.id),
            details_json=json.dumps(
                {"revision_no": revision.revision_no, **details},
                ensure_ascii=False,
            ),
        )
    )


def _manager_assignment_ids(session: Session, actor: Employee) -> list[int]:
    if actor.system_role != "manager":
        raise ReviewOperationError("Действие доступно только руководителю.", 403)
    return list(
        session.scalars(
            select(Assignment.id).where(
                Assignment.employee_id == actor.id,
            )
        ).all()
    )


def _profile_options():
    return (
        selectinload(EmployeeProfile.participant).selectinload(CampaignParticipant.campaign),
        selectinload(EmployeeProfile.participant)
        .selectinload(CampaignParticipant.assignment)
        .selectinload(Assignment.employee),
        selectinload(EmployeeProfile.participant)
        .selectinload(CampaignParticipant.assignment)
        .selectinload(Assignment.staffing_line)
        .selectinload(StaffingLine.org_unit),
        selectinload(EmployeeProfile.revisions),
        selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.revision),
        selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.actor),
    )


def _direct_profile_query(session: Session, actor: Employee):
    manager_assignment_ids = _manager_assignment_ids(session, actor)
    if not manager_assignment_ids:
        return select(EmployeeProfile).where(EmployeeProfile.id == -1)
    return (
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.assignment)
        .join(CampaignParticipant.campaign)
        .where(
            Assignment.manager_assignment_id.in_(manager_assignment_ids),
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
            Campaign.status == "active",
        )
        .options(*_profile_options())
    )


def _latest_revision(profile: EmployeeProfile) -> ProfileRevision | None:
    return max(profile.revisions, key=lambda item: item.revision_no, default=None)


def _assisted_sections(revision: ProfileRevision) -> dict[str, object]:
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


def _serialize_review(profile: EmployeeProfile, questions: list[dict[str, object]]) -> dict[str, object]:
    assignment = profile.participant.assignment
    latest = _latest_revision(profile)
    return {
        "id": profile.id,
        "employee_name": assignment.employee.full_name,
        "position_title": assignment.staffing_line.title,
        "org_unit_id": assignment.staffing_line.org_unit_id,
        "unit_name": assignment.staffing_line.org_unit.name,
        "campaign_name": profile.participant.campaign.name,
        "workflow_status": profile.workflow_status,
        "progress_percent": profile.progress_percent,
        "questions": questions,
        "revision_count": len(profile.revisions),
        "latest_revision": (
            {
                "id": latest.id,
                "revision_no": latest.revision_no,
                "submitted_at": latest.submitted_at.isoformat(),
                "assistant_mode": latest.assistant_mode,
                "assistance_level": latest.assistance_level,
                "assisted_sections": _assisted_sections(latest),
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
        "can_take": profile.workflow_status == "submitted" and latest is not None,
        "can_decide": profile.workflow_status in {"under_review", "returned_by_hr"} and latest is not None,
        "returned_by_hr": profile.workflow_status == "returned_by_hr",
    }


def get_review_queue(session: Session, actor: Employee) -> list[dict[str, object]]:
    profiles = session.scalars(_direct_profile_query(session, actor).order_by(EmployeeProfile.id)).all()
    questions = get_effective_profile_questions(session)
    return [_serialize_review(profile, questions) for profile in profiles]


def _get_direct_profile(session: Session, actor: Employee, profile_id: int) -> EmployeeProfile:
    profile = session.scalar(
        _direct_profile_query(session, actor).where(EmployeeProfile.id == profile_id)
    )
    if profile is None:
        raise ReviewOperationError("Профиль подчиненного не найден или недоступен.", 404)
    return profile


def _add_review_event(
    session: Session,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    actor: Employee,
    action: str,
    comment: str | None = None,
) -> None:
    profile.review_events.append(
        ProfileReviewEvent(
            revision=revision,
            actor=actor,
            action=action,
            comment=comment,
        )
    )


def _apply_return_for_revision(
    session: Session,
    actor: Employee,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    reason: str,
) -> None:
    source_status = profile.workflow_status
    profile.workflow_status = "returned_for_revision"
    profile.last_activity_at = _now()
    _add_review_event(session, profile, revision, actor, "returned", reason)
    _audit(
        session,
        actor,
        "profile.returned_for_revision",
        profile,
        revision,
        {"reason": reason, "source_status": source_status},
    )


def take_for_review(session: Session, actor: Employee, profile_id: int) -> dict[str, object]:
    profile = _get_direct_profile(session, actor, profile_id)
    revision = _latest_revision(profile)
    if profile.workflow_status != "submitted" or revision is None:
        raise ReviewOperationError("Взять на проверку можно только отправленную версию.", 409)
    now = _now()
    revision.locked_at = now
    profile.workflow_status = "under_review"
    profile.last_activity_at = now
    _add_review_event(session, profile, revision, actor, "taken")
    _audit(session, actor, "profile.review_started", profile, revision, {})
    session.flush()
    return _serialize_review(profile, get_effective_profile_questions(session))


def return_for_revision(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ReviewReturnRequest,
) -> dict[str, object]:
    profile = _get_direct_profile(session, actor, profile_id)
    revision = _latest_revision(profile)
    source_status = profile.workflow_status
    if source_status not in {"under_review", "returned_by_hr"} or revision is None:
        raise ReviewOperationError("Вернуть можно только версию на рассмотрении руководителя.", 409)
    _apply_return_for_revision(session, actor, profile, revision, request.reason)
    session.flush()
    return _serialize_review(profile, get_effective_profile_questions(session))


def bulk_return_for_revision(
    session: Session,
    actor: Employee,
    request: BulkReviewReturnRequest,
) -> dict[str, object]:
    available = session.scalars(_direct_profile_query(session, actor).order_by(EmployeeProfile.id)).all()
    selection = "profiles" if request.profile_ids else "org_unit"
    if request.profile_ids:
        requested_ids = set(request.profile_ids)
        selected = [profile for profile in available if profile.id in requested_ids]
        if {profile.id for profile in selected} != requested_ids:
            raise ReviewOperationError("Один или несколько профилей недоступны руководителю.", 404)
        invalid = [
            profile.id
            for profile in selected
            if profile.workflow_status not in {"under_review", "returned_by_hr"}
            or _latest_revision(profile) is None
        ]
        if invalid:
            raise ReviewOperationError(
                "Все выбранные профили должны находиться на рассмотрении руководителя.",
                409,
            )
    else:
        visible_unit_ids = _visible_unit_ids(session, actor) | _visible_unit_ids(session, actor, is_demo=False)
        if request.org_unit_id not in visible_unit_ids:
            raise ReviewOperationError("Подразделение недоступно руководителю.", 404)
        units = session.scalars(select(OrgUnit)).all()
        branch_unit_ids = _unit_descendants(units, {request.org_unit_id})
        selected = [
            profile
            for profile in available
            if profile.participant.assignment.staffing_line.org_unit_id in branch_unit_ids
            and profile.workflow_status in {"under_review", "returned_by_hr"}
            and _latest_revision(profile) is not None
        ]
        if not selected:
            raise ReviewOperationError(
                "В выбранной ветке нет профилей, готовых к возврату руководителем.",
                409,
            )

    for profile in selected:
        revision = _latest_revision(profile)
        assert revision is not None
        _apply_return_for_revision(session, actor, profile, revision, request.reason)
    returned_ids = [profile.id for profile in selected]
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="profiles.bulk_returned_for_revision",
            entity_type="profile_review_batch",
            entity_id=f"manager:{actor.id}",
            details_json=json.dumps(
                {
                    "selection": selection,
                    "org_unit_id": request.org_unit_id,
                    "profile_ids": returned_ids,
                    "returned_count": len(returned_ids),
                    "reason": request.reason,
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return {
        "selection": selection,
        "org_unit_id": request.org_unit_id,
        "profile_ids": returned_ids,
        "returned_count": len(returned_ids),
        "reason": request.reason,
    }


def verify_profile(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ReviewVerifyRequest,
) -> dict[str, object]:
    profile = _get_direct_profile(session, actor, profile_id)
    revision = _latest_revision(profile)
    source_status = profile.workflow_status
    if source_status not in {"under_review", "returned_by_hr"} or revision is None:
        raise ReviewOperationError("Подтвердить можно только версию на рассмотрении руководителя.", 409)
    profile.workflow_status = "manager_verified"
    profile.last_activity_at = _now()
    _add_review_event(session, profile, revision, actor, "verified", request.comment)
    _audit(
        session,
        actor,
        "profile.manager_verified",
        profile,
        revision,
        {"comment": request.comment, "source_status": source_status},
    )
    session.flush()
    return _serialize_review(profile, get_effective_profile_questions(session))
