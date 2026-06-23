from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee, EmployeeProfile, OrgUnit, ProfileRevision
from ..organization.service import unit_descendants, visible_unit_ids
from ..profiles.questionnaire import get_effective_profile_questions
from ..profiles.time import now
from . import repository
from .audit import add_review_event, audit_review_action
from .errors import ReviewOperationError
from .rules import can_manager_decide, can_take_for_review
from .schemas import BulkReviewReturnRequest, ReviewReturnRequest, ReviewVerifyRequest
from .serializers import latest_revision, serialize_review
from ..notifications.service import create_notification, notify_hr_users


def get_review_queue(session: Session, actor: Employee) -> list[dict[str, object]]:
    profiles = repository.load_review_queue(session, actor)
    questions = get_effective_profile_questions(session)
    return [serialize_review(profile, questions) for profile in profiles]


def get_direct_profile(session: Session, actor: Employee, profile_id: int) -> EmployeeProfile:
    profile = repository.load_direct_profile(session, actor, profile_id)
    if profile is None:
        raise ReviewOperationError("Профиль подчиненного не найден или недоступен.", 404)
    return profile


def apply_return_for_revision(
    session: Session,
    actor: Employee,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    reason: str,
) -> None:
    source_status = profile.workflow_status
    profile.workflow_status = "returned_for_revision"
    profile.last_activity_at = now()
    add_review_event(profile, revision, actor, "returned", reason)
    audit_review_action(
        session,
        actor,
        "profile.returned_for_revision",
        profile,
        revision,
        {"reason": reason, "source_status": source_status},
    )
    employee = profile.participant.assignment.employee
    create_notification(
        session,
        recipient_id=employee.id,
        notification_type="profile_returned",
        title="Профиль возвращён на доработку",
        message=f"Руководитель вернул профиль на доработку: {reason}",
        target_section="profile",
        entity_type="employee_profile",
        entity_id=profile.id,
        dedupe_key=f"manager-returned:{revision.id}",
    )


def take_for_review(session: Session, actor: Employee, profile_id: int) -> dict[str, object]:
    profile = get_direct_profile(session, actor, profile_id)
    revision = latest_revision(profile)
    if not can_take_for_review(profile.workflow_status, revision is not None):
        raise ReviewOperationError("Взять на проверку можно только отправленную версию.", 409)
    current_time = now()
    revision.locked_at = current_time
    profile.workflow_status = "under_review"
    profile.last_activity_at = current_time
    add_review_event(profile, revision, actor, "taken")
    audit_review_action(session, actor, "profile.review_started", profile, revision, {})
    session.flush()
    return serialize_review(profile, get_effective_profile_questions(session))


def return_for_revision(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: ReviewReturnRequest,
) -> dict[str, object]:
    profile = get_direct_profile(session, actor, profile_id)
    revision = latest_revision(profile)
    if not can_manager_decide(profile.workflow_status, revision is not None):
        raise ReviewOperationError("Вернуть можно только версию на рассмотрении руководителя.", 409)
    apply_return_for_revision(session, actor, profile, revision, request.reason)
    session.flush()
    return serialize_review(profile, get_effective_profile_questions(session))


def bulk_return_for_revision(
    session: Session,
    actor: Employee,
    request: BulkReviewReturnRequest,
) -> dict[str, object]:
    available = repository.load_review_queue(session, actor)
    selection = "profiles" if request.profile_ids else "org_unit"
    if request.profile_ids:
        selected = _select_profiles_by_ids(available, set(request.profile_ids))
    else:
        selected = _select_profiles_by_unit(session, actor, available, request.org_unit_id)

    for profile in selected:
        revision = latest_revision(profile)
        assert revision is not None
        apply_return_for_revision(session, actor, profile, revision, request.reason)
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
    profile = get_direct_profile(session, actor, profile_id)
    revision = latest_revision(profile)
    source_status = profile.workflow_status
    if not can_manager_decide(source_status, revision is not None):
        raise ReviewOperationError("Подтвердить можно только версию на рассмотрении руководителя.", 409)
    profile.workflow_status = "manager_verified"
    profile.last_activity_at = now()
    add_review_event(profile, revision, actor, "verified", request.comment)
    audit_review_action(
        session,
        actor,
        "profile.manager_verified",
        profile,
        revision,
        {"comment": request.comment, "source_status": source_status},
    )
    employee = profile.participant.assignment.employee
    notify_hr_users(
        session,
        is_demo=profile.participant.campaign.is_demo,
        notification_type="profile_manager_verified",
        title="Профиль подтверждён руководителем",
        message=f"Профиль сотрудника {employee.full_name} ожидает решения HR.",
        target_section="hr-reviews",
        entity_type="employee_profile",
        entity_id=profile.id,
        dedupe_key=f"manager-verified:{revision.id}",
        exclude_employee_id=actor.id,
    )
    session.flush()
    return serialize_review(profile, get_effective_profile_questions(session))


def _select_profiles_by_ids(
    available: list[EmployeeProfile],
    requested_ids: set[int],
) -> list[EmployeeProfile]:
    selected = [profile for profile in available if profile.id in requested_ids]
    if {profile.id for profile in selected} != requested_ids:
        raise ReviewOperationError("Один или несколько профилей недоступны руководителю.", 404)
    invalid = [
        profile.id
        for profile in selected
        if not can_manager_decide(profile.workflow_status, latest_revision(profile) is not None)
    ]
    if invalid:
        raise ReviewOperationError(
            "Все выбранные профили должны находиться на рассмотрении руководителя.",
            409,
        )
    return selected


def _select_profiles_by_unit(
    session: Session,
    actor: Employee,
    available: list[EmployeeProfile],
    org_unit_id: int,
) -> list[EmployeeProfile]:
    visible_ids = visible_unit_ids(session, actor) | visible_unit_ids(session, actor, is_demo=False)
    if org_unit_id not in visible_ids:
        raise ReviewOperationError("Подразделение недоступно руководителю.", 404)
    units = session.scalars(select(OrgUnit)).all()
    branch_unit_ids = unit_descendants(units, {org_unit_id})
    selected = [
        profile
        for profile in available
        if profile.participant.assignment.staffing_line.org_unit_id in branch_unit_ids
        and can_manager_decide(profile.workflow_status, latest_revision(profile) is not None)
    ]
    if not selected:
        raise ReviewOperationError(
            "В выбранной ветке нет профилей, готовых к возврату руководителем.",
            409,
        )
    return selected


_get_direct_profile = get_direct_profile
_apply_return_for_revision = apply_return_for_revision
