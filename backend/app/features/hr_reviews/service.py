from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee, EmployeeProfile, OrgUnit, ProfileRevision
from ..organization.service import unit_descendants, visible_unit_ids
from ..profiles.questionnaire import get_effective_profile_questions
from ..profiles.time import now
from . import repository
from .audit import record_review_action
from .errors import HrReviewOperationError
from .rules import can_hr_decide
from .schemas import BulkReviewReturnRequest, ReviewReturnRequest, ReviewVerifyRequest
from .serializers import latest_revision, serialize_review
from ..notifications.service import create_notification


def get_hr_review_queue(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    profiles = repository.load_hr_review_queue(session, is_demo=is_demo)
    questions = get_effective_profile_questions(session)
    return [serialize_review(profile, questions) for profile in profiles]


def get_profile(session: Session, profile_id: int, is_demo: bool = True) -> EmployeeProfile:
    profile = repository.load_profile(session, profile_id, is_demo=is_demo)
    if profile is None:
        raise HrReviewOperationError("Профиль для HR-проверки не найден.", 404)
    return profile


def accept_profile(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ReviewVerifyRequest,
    is_demo: bool = True,
) -> dict[str, object]:
    profile = get_profile(session, profile_id, is_demo)
    revision = latest_revision(profile)
    if not can_hr_decide(profile.workflow_status, revision is not None):
        raise HrReviewOperationError("Принять можно только профиль, подтвержденный руководителем.", 409)
    profile.workflow_status = "hr_accepted"
    profile.last_activity_at = now()
    record_review_action(
        session,
        actor,
        profile,
        revision,
        "hr_accepted",
        "profile.hr_accepted",
        request.comment,
    )
    employee = profile.participant.assignment.employee
    create_notification(
        session,
        recipient_id=employee.id,
        notification_type="profile_accepted",
        title="Профиль принят HR",
        message="Проверка профиля завершена. Профиль принят HR.",
        target_section="profile",
        entity_type="employee_profile",
        entity_id=profile.id,
        dedupe_key=f"hr-accepted:{revision.id}",
    )
    session.flush()
    return serialize_review(profile, get_effective_profile_questions(session))


def return_to_manager(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ReviewReturnRequest,
    is_demo: bool = True,
) -> dict[str, object]:
    profile = get_profile(session, profile_id, is_demo)
    revision = latest_revision(profile)
    if not can_hr_decide(profile.workflow_status, revision is not None):
        raise HrReviewOperationError("Вернуть на доработку можно только профиль, готовый к решению HR.", 409)
    assert revision is not None
    _return_profile_from_hr(session, actor, profile, revision, request.reason)
    session.flush()
    return serialize_review(profile, get_effective_profile_questions(session))


def bulk_return_to_manager(
    session: Session,
    actor: Employee,
    request: BulkReviewReturnRequest,
    is_demo: bool = True,
) -> dict[str, object]:
    available = repository.load_hr_review_queue(session, is_demo=is_demo)
    selection = "profiles" if request.profile_ids else "org_unit"
    if request.profile_ids:
        selected = _select_profiles_by_ids(available, set(request.profile_ids))
    else:
        selected = _select_profiles_by_unit(session, actor, available, request.org_unit_id, is_demo)

    for profile in selected:
        revision = latest_revision(profile)
        assert revision is not None
        _return_profile_from_hr(session, actor, profile, revision, request.reason)
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


def _return_profile_from_hr(
    session: Session,
    actor: Employee,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    reason: str,
) -> None:
    assignment = profile.participant.assignment
    manager = assignment.manager
    direct_hr_route = manager is None
    profile.workflow_status = "returned_for_revision" if direct_hr_route else "returned_by_hr"
    profile.last_activity_at = now()
    record_review_action(
        session,
        actor,
        profile,
        revision,
        "hr_returned",
        "profile.returned_for_revision_by_hr" if direct_hr_route else "profile.returned_by_hr",
        reason,
    )

    recipient_id = assignment.employee_id if direct_hr_route else manager.employee_id
    employee_name = assignment.employee.full_name
    create_notification(
        session,
        recipient_id=recipient_id,
        notification_type="profile_returned_by_hr",
        title="HR вернул профиль",
        message=f"Профиль сотрудника {employee_name} возвращён HR: {reason}",
        target_section="profile" if direct_hr_route else "manager-reviews",
        entity_type="employee_profile",
        entity_id=profile.id,
        dedupe_key=f"hr-returned:{revision.id}",
    )


def _select_profiles_by_ids(
    available: list[EmployeeProfile],
    requested_ids: set[int],
) -> list[EmployeeProfile]:
    selected = [profile for profile in available if profile.id in requested_ids]
    if {profile.id for profile in selected} != requested_ids:
        raise HrReviewOperationError("Один или несколько профилей недоступны HR.", 404)
    if any(
        not can_hr_decide(profile.workflow_status, latest_revision(profile) is not None)
        for profile in selected
    ):
        raise HrReviewOperationError("Все выбранные профили должны быть подтверждены руководителем.", 409)
    return selected


def _select_profiles_by_unit(
    session: Session,
    actor: Employee,
    available: list[EmployeeProfile],
    org_unit_id: int,
    is_demo: bool,
) -> list[EmployeeProfile]:
    if org_unit_id not in visible_unit_ids(session, actor, is_demo=is_demo):
        raise HrReviewOperationError("Подразделение недоступно HR.", 404)
    units = session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(is_demo))).all()
    branch_unit_ids = unit_descendants(units, {org_unit_id})
    selected = [
        profile
        for profile in available
        if profile.participant.assignment.staffing_line.org_unit_id in branch_unit_ids
        and can_hr_decide(profile.workflow_status, latest_revision(profile) is not None)
    ]
    if not selected:
        raise HrReviewOperationError("В выбранной ветке нет профилей, готовых к возврату HR.", 409)
    return selected


_get_profile = get_profile
