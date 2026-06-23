from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Employee, StaffingLine
from .schemas import WorkStaffingLineCreate
from . import repository
from .audit import audit
from .deletion import active_wave_warning_message, active_wave_warnings, delete_assignments
from .employees import ensure_unique_new_emails, load_manager_assignments
from .errors import StructureOperationError
from .rules import requested_fte
from .work_assignments import create_work_assignment


def create_work_staffing_line(
    session: Session,
    actor: Employee,
    org_unit_id: int,
    request: WorkStaffingLineCreate,
) -> dict[str, object]:
    unit = repository.load_work_unit(session, org_unit_id)
    if unit is None:
        raise StructureOperationError("Рабочее подразделение не найдено.", 404)

    duplicate = repository.find_duplicate_active_work_line(
        session,
        org_unit_id=unit.id,
        title=request.title,
    )
    if duplicate is not None:
        raise StructureOperationError("В подразделении уже есть активная штатная строка с таким названием.", 409)

    requested = requested_fte(request.employees)
    if requested > request.approved_fte + 1e-9:
        raise StructureOperationError(
            f"Недостаточно ставок в новой строке: доступно {request.approved_fte}, запрошено {requested}.",
            409,
        )
    ensure_unique_new_emails(session, [employee.email for employee in request.employees])
    manager_ids = {
        employee.manager_assignment_id
        for employee in request.employees
        if employee.manager_assignment_id is not None
    }
    managers = load_manager_assignments(session, manager_ids, is_demo=False)

    line = StaffingLine(
        org_unit=unit,
        title=request.title,
        approved_fte=round(request.approved_fte, 4),
        reported_occupied_fte=0,
        is_demo=False,
        is_active=True,
    )
    session.add(line)
    session.flush()

    added = [
        create_work_assignment(session, line, employee, managers.get(employee.manager_assignment_id))
        for employee in request.employees
    ]
    audit(
        session,
        actor,
        "staffing_line.work_created",
        "staffing_line",
        line.id,
        {
            "scope": "work",
            "org_unit_id": unit.id,
            "org_unit_name": unit.name,
            "staffing_title": line.title,
            "approved_fte": line.approved_fte,
            "employees_count": len(added),
            "employee_assignment_ids": [item["assignment_id"] for item in added],
        },
    )
    session.flush()
    return {
        "scope": "work",
        "org_unit_id": unit.id,
        "org_unit_name": unit.name,
        "staffing_line_id": line.id,
        "staffing_title": line.title,
        "approved_fte": line.approved_fte,
        "added": added,
        "remaining_fte": round(line.approved_fte - requested, 2),
    }


def delete_work_staffing_line(
    session: Session,
    actor: Employee,
    staffing_line_id: int,
    *,
    force: bool = False,
) -> dict[str, object]:
    line = repository.load_staffing_line(session, staffing_line_id, is_demo=False)
    if line is None:
        raise StructureOperationError("Штатная строка не найдена.", 404)

    assignment_ids = {assignment.id for assignment in line.assignments}
    warnings = active_wave_warnings(session, assignment_ids)
    if warnings and not force:
        raise StructureOperationError(active_wave_warning_message(warnings), 409)

    deleted = delete_assignments(session, actor, assignment_ids)
    links = repository.load_document_links_for_work_line(session, line.id)
    for link in links:
        session.delete(link)

    staffing_title = line.title
    org_unit_id = line.org_unit_id
    org_unit_name = line.org_unit.name
    session.delete(line)
    audit(
        session,
        actor,
        "staffing_line.work_deleted",
        "staffing_line",
        staffing_line_id,
        {
            "scope": "work",
            "staffing_title": staffing_title,
            "org_unit_id": org_unit_id,
            "org_unit_name": org_unit_name,
            "document_links_deleted": len(links),
            "force": force,
            **deleted,
        },
    )
    session.flush()
    return {
        "scope": "work",
        "staffing_line_id": staffing_line_id,
        "document_links_deleted": len(links),
        **deleted,
    }
