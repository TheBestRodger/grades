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


class HrReviewOperationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _options():
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


def _serialize(profile: EmployeeProfile, questions: list[dict[str, object]]) -> dict[str, object]:
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
        "can_decide": profile.workflow_status == "manager_verified" and latest is not None,
    }


def _query(is_demo: bool = True):
    return (
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.campaign)
        .where(
            Campaign.is_demo.is_(is_demo),
            Campaign.status == "active",
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
        )
        .options(*_options())
    )


def get_hr_review_queue(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    profiles = session.scalars(_query(is_demo).order_by(EmployeeProfile.id)).all()
    questions = get_effective_profile_questions(session)
    return [_serialize(profile, questions) for profile in profiles]


def _get_profile(session: Session, profile_id: int, is_demo: bool = True) -> EmployeeProfile:
    profile = session.scalar(_query(is_demo).where(EmployeeProfile.id == profile_id))
    if profile is None:
        raise HrReviewOperationError("Профиль для HR-проверки не найден.", 404)
    return profile


def _record(
    session: Session,
    actor: Employee,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    action: str,
    audit_action: str,
    comment: str | None,
) -> None:
    profile.review_events.append(
        ProfileReviewEvent(
            revision=revision,
            actor=actor,
            action=action,
            comment=comment,
        )
    )
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=audit_action,
            entity_type="employee_profile",
            entity_id=str(profile.id),
            details_json=json.dumps(
                {"revision_no": revision.revision_no, "comment": comment},
                ensure_ascii=False,
            ),
        )
    )


def accept_profile(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ReviewVerifyRequest,
    is_demo: bool = True,
) -> dict[str, object]:
    profile = _get_profile(session, profile_id, is_demo)
    revision = _latest_revision(profile)
    if profile.workflow_status != "manager_verified" or revision is None:
        raise HrReviewOperationError(
            "Принять можно только профиль, подтвержденный руководителем.",
            409,
        )
    profile.workflow_status = "hr_accepted"
    profile.last_activity_at = _now()
    _record(
        session,
        actor,
        profile,
        revision,
        "hr_accepted",
        "profile.hr_accepted",
        request.comment,
    )
    session.flush()
    return _serialize(profile, get_effective_profile_questions(session))


def return_to_manager(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ReviewReturnRequest,
    is_demo: bool = True,
) -> dict[str, object]:
    profile = _get_profile(session, profile_id, is_demo)
    revision = _latest_revision(profile)
    if profile.workflow_status != "manager_verified" or revision is None:
        raise HrReviewOperationError(
            "Вернуть руководителю можно только подтвержденный им профиль.",
            409,
        )
    profile.workflow_status = "returned_by_hr"
    profile.last_activity_at = _now()
    _record(
        session,
        actor,
        profile,
        revision,
        "hr_returned",
        "profile.returned_by_hr",
        request.reason,
    )
    session.flush()
    return _serialize(profile, get_effective_profile_questions(session))


def bulk_return_to_manager(
    session: Session,
    actor: Employee,
    request: BulkReviewReturnRequest,
    is_demo: bool = True,
) -> dict[str, object]:
    available = session.scalars(_query(is_demo).order_by(EmployeeProfile.id)).all()
    selection = "profiles" if request.profile_ids else "org_unit"
    if request.profile_ids:
        requested_ids = set(request.profile_ids)
        selected = [profile for profile in available if profile.id in requested_ids]
        if {profile.id for profile in selected} != requested_ids:
            raise HrReviewOperationError("Один или несколько профилей недоступны HR.", 404)
        if any(
            profile.workflow_status != "manager_verified" or _latest_revision(profile) is None
            for profile in selected
        ):
            raise HrReviewOperationError(
                "Все выбранные профили должны быть подтверждены руководителем.",
                409,
            )
    else:
        visible_unit_ids = _visible_unit_ids(session, actor, is_demo=is_demo)
        if request.org_unit_id not in visible_unit_ids:
            raise HrReviewOperationError("Подразделение недоступно HR.", 404)
        units = session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(is_demo))).all()
        branch_unit_ids = _unit_descendants(units, {request.org_unit_id})
        selected = [
            profile
            for profile in available
            if profile.participant.assignment.staffing_line.org_unit_id in branch_unit_ids
            and profile.workflow_status == "manager_verified"
            and _latest_revision(profile) is not None
        ]
        if not selected:
            raise HrReviewOperationError(
                "В выбранной ветке нет профилей, готовых к возврату HR.",
                409,
            )

    for profile in selected:
        revision = _latest_revision(profile)
        assert revision is not None
        profile.workflow_status = "returned_by_hr"
        profile.last_activity_at = _now()
        _record(
            session,
            actor,
            profile,
            revision,
            "hr_returned",
            "profile.returned_by_hr",
            request.reason,
        )
    returned_ids = [profile.id for profile in selected]
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="profiles.bulk_returned_by_hr",
            entity_type="profile_review_batch",
            entity_id=f"hr:{actor.id}",
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
