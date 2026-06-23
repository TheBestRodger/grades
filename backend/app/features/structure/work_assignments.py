from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Assignment, Employee, StaffingLine
from .schemas import WorkStaffingEmployeeCreate
from ..organization.service import resolve_manager_assignment_for_line
from .credentials import login_from_email
from .rules import effective_is_hr


def create_work_assignment(
    session: Session,
    line: StaffingLine,
    item: WorkStaffingEmployeeCreate,
    manager: Assignment | None,
) -> dict[str, object]:
    resolved_manager = manager
    if resolved_manager is None:
        resolved_manager = resolve_manager_assignment_for_line(session, line)
    employee = Employee(
        full_name=item.full_name,
        email=item.email,
        username=login_from_email(item.email),
        system_role=item.system_role,
        is_hr=effective_is_hr(item.system_role, item.is_hr),
        is_demo=False,
    )
    session.add(employee)
    session.flush()
    assignment = Assignment(
        employee=employee,
        staffing_line=line,
        manager_assignment_id=resolved_manager.id if resolved_manager else None,
        fte=item.fte,
        assignment_role="primary",
        is_demo=False,
    )
    session.add(assignment)
    session.flush()
    return {
        "employee_id": employee.id,
        "assignment_id": assignment.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "fte": assignment.fte,
        "system_role": employee.system_role,
        "is_hr": employee.is_hr,
        "manager_assignment_id": assignment.manager_assignment_id,
    }


_create_work_assignment = create_work_assignment
