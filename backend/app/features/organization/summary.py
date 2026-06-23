from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Employee
from . import repository
from .hierarchy import assigned_fte, visible_unit_ids
from .rules import can_view_employee_only_scope


def organization_summary(session: Session, actor: Employee, is_demo: bool = True) -> dict[str, object]:
    if can_view_employee_only_scope(actor) and is_demo:
        return {
            "scope": "self",
            "employees": 1,
            "staffing_lines": None,
            "approved_fte": None,
            "assigned_fte": None,
            "vacancy_fte": None,
        }

    unit_ids = visible_unit_ids(session, actor, is_demo)
    if not unit_ids:
        return {
            "scope": "work" if not is_demo else actor.system_role,
            "employees": 0,
            "staffing_lines": 0,
            "approved_fte": 0,
            "assigned_fte": 0,
            "vacancy_fte": 0,
        }
    lines = repository.load_summary_lines(session, unit_ids)
    employees = {assignment.employee_id for line in lines for assignment in line.assignments}
    approved = round(sum(line.approved_fte for line in lines), 2)
    assigned = round(sum(assigned_fte(line) for line in lines), 2)
    return {
        "scope": actor.system_role if is_demo else "work",
        "employees": len(employees),
        "staffing_lines": len(lines),
        "approved_fte": approved,
        "assigned_fte": assigned,
        "vacancy_fte": round(approved - assigned, 2),
    }
