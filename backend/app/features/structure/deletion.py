from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Assignment, AuthSession, CampaignParticipant, Employee
from . import repository
from .audit import audit
from .credentials import archive_employee_email
from .errors import StructureOperationError

WAVE_STATUS_ACTIVE = "active"


def delete_work_assignment(
    session: Session,
    actor: Employee,
    assignment_id: int,
    *,
    force: bool = False,
) -> dict[str, object]:
    assignment = repository.load_assignment(session, assignment_id, is_demo=False)
    if assignment is None:
        raise StructureOperationError("Назначение сотрудника не найдено.", 404)

    warnings = active_wave_warnings(session, {assignment.id})
    if warnings and not force:
        raise StructureOperationError(active_wave_warning_message(warnings), 409)

    employee = assignment.employee
    deleted = delete_assignments(session, actor, {assignment.id})
    audit(
        session,
        actor,
        "assignment.work_deleted",
        "assignment",
        assignment_id,
        {
            "scope": "work",
            "employee_id": employee.id,
            "employee_name": employee.full_name,
            "staffing_line_id": assignment.staffing_line_id,
            "staffing_title": assignment.staffing_line.title,
            "org_unit_id": assignment.staffing_line.org_unit_id,
            "org_unit_name": assignment.staffing_line.org_unit.name,
            "force": force,
            **deleted,
        },
    )
    session.flush()
    return {"scope": "work", "assignment_id": assignment_id, **deleted}


def delete_assignments(session: Session, actor: Employee, assignment_ids: set[int]) -> dict[str, int]:
    if not assignment_ids:
        return {
            "deleted_assignments": 0,
            "deleted_participants": 0,
            "deleted_profiles": 0,
            "deactivated_employees": 0,
        }

    assignments = repository.load_assignments_for_delete(session, assignment_ids)
    employee_ids = {assignment.employee_id for assignment in assignments}
    participants = repository.load_participants_for_assignments(session, assignment_ids)
    profile_count = sum(1 for participant in participants if participant.profile is not None)
    for participant in participants:
        session.delete(participant)

    for report in repository.load_reports_for_managers(session, assignment_ids):
        report.manager_assignment_id = None

    for assignment in assignments:
        session.delete(assignment)

    other_assignments = repository.load_other_assignments_for_employees(
        session,
        employee_ids,
        excluded_assignment_ids=assignment_ids,
    )
    employees_with_other_assignments = {assignment.employee_id for assignment in other_assignments}
    deactivated = _archive_unassigned_employees(
        session,
        actor,
        assignments,
        employees_with_other_assignments,
        assignment_ids,
    )
    return {
        "deleted_assignments": len(assignments),
        "deleted_participants": len(participants),
        "deleted_profiles": profile_count,
        "deactivated_employees": deactivated,
    }


def _archive_unassigned_employees(
    session: Session,
    actor: Employee,
    assignments: list[Assignment],
    employees_with_other_assignments: set[int],
    assignment_ids: set[int],
) -> int:
    deactivated = 0
    now = datetime.utcnow()
    for assignment in assignments:
        employee = assignment.employee
        if employee.id in employees_with_other_assignments:
            continue
        archived_email = archive_employee_email(employee, now)
        original_email = employee.email
        employee.email = archived_email
        if employee.is_active:
            employee.is_active = False
            deactivated += 1
        for auth_session in session.scalars(
            select(AuthSession).where(
                AuthSession.employee_id == employee.id,
                AuthSession.revoked_at.is_(None),
            )
        ).all():
            auth_session.revoked_at = now
        audit(
            session,
            actor,
            "employee.email_archived",
            "employee",
            employee.id,
            {
                "original_email": original_email,
                "archived_email": archived_email,
                "assignment_ids_removed": sorted(assignment_ids),
            },
        )
    return deactivated


def active_wave_warnings(
    session: Session,
    assignment_ids: set[int],
) -> list[dict[str, object]]:
    if not assignment_ids:
        return []
    participants = repository.load_active_wave_participants(session, assignment_ids)
    warnings: list[dict[str, object]] = []
    seen: set[tuple[int | None, int]] = set()
    for participant in participants:
        if participant.wave is None or participant.wave.status != WAVE_STATUS_ACTIVE:
            continue
        key = (participant.campaign_wave_id, participant.assignment_id)
        if key in seen:
            continue
        seen.add(key)
        assignment = participant.assignment
        warnings.append(
            {
                "employee_name": assignment.employee.full_name,
                "staffing_title": assignment.staffing_line.title,
                "org_unit_name": assignment.staffing_line.org_unit.name,
                "campaign_name": participant.campaign.name,
                "wave_name": participant.wave.name,
            }
        )
    return warnings


def active_wave_warning_message(warnings: list[dict[str, object]]) -> str:
    shown = warnings[:5]
    lines = [
        (
            f"{item['employee_name']} — {item['staffing_title']}, "
            f"кампания «{item['campaign_name']}», волна «{item['wave_name']}»"
        )
        for item in shown
    ]
    suffix = "" if len(warnings) <= len(shown) else f" Ещё затронуто: {len(warnings) - len(shown)}."
    return (
        "Объект участвует в активной волне: "
        + "; ".join(lines)
        + ". При подтверждении будут удалены анкеты, ревизии и участие в отчетах."
        + suffix
    )


_active_wave_warnings = active_wave_warnings
_active_wave_warning_message = active_wave_warning_message
_delete_assignments = delete_assignments
