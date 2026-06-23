from __future__ import annotations

from sqlalchemy.orm import Session

from . import repository


def get_manager_options(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    assignments = repository.load_manager_assignments(session, is_demo=is_demo)
    return [
        {
            "assignment_id": assignment.id,
            "employee_name": assignment.employee.full_name,
            "position_title": assignment.staffing_line.title,
            "unit_name": assignment.staffing_line.org_unit.name,
            "is_demo": assignment.is_demo,
        }
        for assignment in assignments
    ]
