from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...hr_operations import (
    add_employees,
    create_work_staffing_line,
    get_manager_options,
)
from ...models import Employee
from ...schemas import BulkEmployeeCreate, WorkStaffingLineCreate
from ...work_employee_import import import_work_assignments
from ..deps import current_hr, get_session
from ..errors import run_operation

router = APIRouter()


@router.get("/api/hr/managers")
def managers(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return get_manager_options(session)


@router.get("/api/work/hr/managers")
def work_managers(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return get_manager_options(session, is_demo=False)


@router.post("/api/hr/staffing-lines/{staffing_line_id}/employees/bulk")
def bulk_add_employees(
    staffing_line_id: int,
    request: BulkEmployeeCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: add_employees(session, actor, staffing_line_id, request)
    )


@router.post("/api/work/hr/employees/import")
async def import_work_employees(
    request: Request,
    filename: str = "employees.csv",
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    content = await request.body()
    return run_operation(
        lambda: import_work_assignments(session, actor, filename, content)
    )


@router.post("/api/work/hr/org-units/{org_unit_id}/staffing-lines")
def add_work_staffing_line(
    org_unit_id: int,
    request: WorkStaffingLineCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: create_work_staffing_line(session, actor, org_unit_id, request)
    )


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
