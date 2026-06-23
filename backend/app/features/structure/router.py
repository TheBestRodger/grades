from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...api.deps import current_hr, get_session
from ...api.errors import run_operation
from ...models import Employee
from .schemas import (
    BulkEmployeeCreate,
    EmployeeAssignmentUpdate,
    WorkStaffingLineCreate,
)
from ..imports.work_employee import import_work_assignments
from .service import (
    add_employees,
    create_work_staffing_line,
    delete_work_assignment,
    delete_work_staffing_line,
    get_manager_options,
    reset_employee_password,
    update_employee_assignment,
)

router = APIRouter()


@router.get("/api/hr/managers")
def managers(
    _: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    return get_manager_options(session)


@router.get("/api/work/hr/managers")
def work_managers(
    _: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    return get_manager_options(session, is_demo=False)


@router.post("/api/hr/staffing-lines/{staffing_line_id}/employees/bulk")
def bulk_add_employees(
    staffing_line_id: int,
    request: BulkEmployeeCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: add_employees(session, actor, staffing_line_id, request))


@router.put("/api/hr/assignments/{assignment_id}/employee")
def update_demo_employee_assignment(
    assignment_id: int,
    request: EmployeeAssignmentUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: update_employee_assignment(session, actor, assignment_id, request)
    )


@router.post("/api/hr/assignments/{assignment_id}/password/reset")
def reset_demo_employee_password(
    assignment_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: reset_employee_password(session, actor, assignment_id))


@router.post("/api/work/hr/employees/import")
async def import_work_employees(
    request: Request,
    filename: str = "employees.csv",
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    content = await request.body()
    return run_operation(lambda: import_work_assignments(session, actor, filename, content))


@router.post("/api/work/hr/org-units/{org_unit_id}/staffing-lines")
def add_work_staffing_line(
    org_unit_id: int,
    request: WorkStaffingLineCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: create_work_staffing_line(session, actor, org_unit_id, request))


@router.post("/api/work/hr/staffing-lines/{staffing_line_id}/employees/bulk")
def bulk_add_work_employees(
    staffing_line_id: int,
    request: BulkEmployeeCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: add_employees(session, actor, staffing_line_id, request, is_demo=False)
    )


@router.put("/api/work/hr/assignments/{assignment_id}/employee")
def update_work_employee_assignment(
    assignment_id: int,
    request: EmployeeAssignmentUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: update_employee_assignment(
            session,
            actor,
            assignment_id,
            request,
            is_demo=False,
        )
    )


@router.post("/api/work/hr/assignments/{assignment_id}/password/reset")
def reset_work_employee_password(
    assignment_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: reset_employee_password(session, actor, assignment_id, is_demo=False)
    )


@router.delete("/api/work/hr/assignments/{assignment_id}")
def remove_work_assignment(
    assignment_id: int,
    force: bool = False,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: delete_work_assignment(session, actor, assignment_id, force=force))


@router.delete("/api/work/hr/staffing-lines/{staffing_line_id}")
def remove_work_staffing_line(
    staffing_line_id: int,
    force: bool = False,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: delete_work_staffing_line(session, actor, staffing_line_id, force=force)
    )
