from __future__ import annotations

from sqlalchemy.orm import Session

from ...features.auth.passwords import generate_temporary_password, hash_password
from ...models import Assignment, Employee
from .schemas import BulkEmployeeCreate, EmployeeAssignmentUpdate
from ..organization.service import resolve_manager_assignment_for_line
from . import repository
from .audit import audit
from .credentials import login_from_email
from .errors import StructureOperationError
from .rules import effective_is_hr, has_enough_fte, remaining_fte, requested_fte
from ..notifications.service import create_notification


def add_employees(
    session: Session,
    actor: Employee,
    staffing_line_id: int,
    request: BulkEmployeeCreate,
    *,
    is_demo: bool = True,
) -> dict[str, object]:
    line = repository.load_staffing_line(session, staffing_line_id, is_demo=is_demo)
    if line is None:
        raise StructureOperationError("Позиция не найдена.", 404)

    requested = requested_fte(request.employees)
    available = remaining_fte(line)
    if not has_enough_fte(line, requested):
        raise StructureOperationError(
            f"Недостаточно свободных ставок: доступно {available}, запрошено {requested}.",
            409,
        )

    emails = [employee.email for employee in request.employees]
    ensure_unique_new_emails(session, emails)

    manager_ids = {
        employee.manager_assignment_id
        for employee in request.employees
        if employee.manager_assignment_id is not None
    }
    managers = load_manager_assignments(session, manager_ids, is_demo=is_demo)

    added: list[dict[str, object]] = []
    for item in request.employees:
        resolved_manager = (
            managers[item.manager_assignment_id]
            if item.manager_assignment_id is not None
            else resolve_manager_assignment_for_line(session, line)
        )
        temporary_password = generate_temporary_password()
        employee = Employee(
            full_name=item.full_name,
            email=item.email,
            username=login_from_email(item.email),
            password_hash=hash_password(temporary_password),
            system_role=item.system_role,
            is_hr=effective_is_hr(item.system_role, item.is_hr),
            is_demo=is_demo,
        )
        session.add(employee)
        session.flush()
        assignment = Assignment(
            employee=employee,
            staffing_line=line,
            manager_assignment_id=resolved_manager.id if resolved_manager is not None else None,
            fte=item.fte,
            is_demo=is_demo,
        )
        session.add(assignment)
        session.flush()
        create_notification(
            session,
            recipient_id=employee.id,
            notification_type="employee_added",
            title="Вы добавлены в систему",
            message=f"Вам назначена должность «{line.title}».",
            target_section="profile",
            entity_type="assignment",
            entity_id=assignment.id,
            dedupe_key=f"employee-added:{employee.id}",
        )
        added.append(
            {
                "employee_id": employee.id,
                "assignment_id": assignment.id,
                "full_name": employee.full_name,
                "email": employee.email,
                "username": employee.username,
                "password": temporary_password,
                "fte": assignment.fte,
                "system_role": employee.system_role,
                "is_hr": employee.is_hr,
                "manager_assignment_id": assignment.manager_assignment_id,
            }
        )

    audit_added = [{key: value for key, value in employee.items() if key != "password"} for employee in added]
    audit(
        session,
        actor,
        "employees.bulk_added",
        "staffing_line",
        line.id,
        {
            "scope": "demo" if is_demo else "work",
            "staffing_title": line.title,
            "count": len(added),
            "employees": audit_added,
        },
    )
    return {
        "staffing_line_id": line.id,
        "staffing_title": line.title,
        "added": added,
        "remaining_fte": round(available - requested, 2),
    }


def update_employee_assignment(
    session: Session,
    actor: Employee,
    assignment_id: int,
    request: EmployeeAssignmentUpdate,
    *,
    is_demo: bool = True,
) -> dict[str, object]:
    assignment = repository.load_assignment(session, assignment_id, is_demo=is_demo)
    if assignment is None:
        raise StructureOperationError("Назначение не найдено.", 404)

    employee = assignment.employee
    duplicate_email = repository.find_duplicate_employee_email(session, request.email, exclude_employee_id=employee.id)
    if duplicate_email is not None:
        raise StructureOperationError("Сотрудник с таким email уже существует.", 409)

    employee.full_name = request.full_name
    employee.email = request.email
    employee.username = login_from_email(request.email)
    employee.system_role = request.system_role
    employee.is_hr = effective_is_hr(request.system_role, request.is_hr)

    session.flush()
    audit(
        session,
        actor,
        "employee.updated",
        "assignment",
        assignment.id,
        {
            "scope": "demo" if is_demo else "work",
            "assignment_id": assignment.id,
            "employee_id": employee.id,
            "full_name": employee.full_name,
            "email": employee.email,
            "system_role": employee.system_role,
            "is_hr": employee.is_hr,
        },
    )
    return {
        "assignment_id": assignment.id,
        "employee_id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "system_role": employee.system_role,
        "is_hr": employee.is_hr,
        "manager_assignment_id": assignment.manager_assignment_id,
        "staffing_line_id": assignment.staffing_line_id,
        "staffing_title": assignment.staffing_line.title,
        "unit_name": assignment.staffing_line.org_unit.name,
    }


def ensure_unique_new_emails(session: Session, emails: list[str]) -> None:
    if len(emails) != len(set(emails)):
        raise StructureOperationError("В списке добавления есть повторяющиеся email.")
    existing_email = repository.find_existing_email(session, emails)
    if existing_email is not None:
        raise StructureOperationError(f"Сотрудник с email {existing_email} уже существует.", 409)


def load_manager_assignments(
    session: Session,
    manager_ids: set[int],
    *,
    is_demo: bool,
) -> dict[int | None, Assignment]:
    managers = repository.load_manager_assignments(session, manager_ids, is_demo=is_demo)
    if set(managers) != manager_ids:
        raise StructureOperationError("Выбранный руководитель не найден в структуре.")
    return managers


_ensure_unique_new_emails = ensure_unique_new_emails
_load_manager_assignments = load_manager_assignments
