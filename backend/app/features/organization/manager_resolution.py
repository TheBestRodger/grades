from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Assignment, StaffingLine
from . import repository


def resolve_manager_assignment_for_unit(
    session: Session,
    org_unit_id: int,
    *,
    is_demo: bool,
    exclude_employee_id: int | None = None,
) -> Assignment | None:
    units = repository.load_units_with_parent(session, is_demo=is_demo)
    units_by_id = {unit.id: unit for unit in units}
    visited: set[int] = set()
    current_unit_id: int | None = org_unit_id

    while current_unit_id is not None and current_unit_id not in visited:
        visited.add(current_unit_id)
        candidates = repository.load_manager_candidates_for_unit(
            session,
            current_unit_id,
            is_demo=is_demo,
            exclude_employee_id=exclude_employee_id,
        )
        if candidates:
            return sorted(candidates, key=_manager_sort_key)[0]
        current_unit = units_by_id.get(current_unit_id)
        current_unit_id = current_unit.parent_id if current_unit is not None else None

    return None


def resolve_manager_assignment_for_line(
    session: Session,
    line: StaffingLine,
    *,
    exclude_employee_id: int | None = None,
) -> Assignment | None:
    return resolve_manager_assignment_for_unit(
        session,
        line.org_unit_id,
        is_demo=line.is_demo,
        exclude_employee_id=exclude_employee_id,
    )


def _manager_sort_key(assignment: Assignment) -> tuple[int, str, str, str, int]:
    title_rank, normalized_title = _manager_title_rank(assignment.staffing_line.title)
    return (
        title_rank,
        normalized_title,
        assignment.staffing_line.title.lower(),
        assignment.employee.full_name.lower(),
        assignment.id,
    )


def _manager_title_rank(title: str) -> tuple[int, str]:
    normalized = title.lower()
    if "началь" in normalized:
        return 0, normalized
    if "руковод" in normalized:
        return 1, normalized
    if "директор" in normalized:
        return 2, normalized
    if "завед" in normalized:
        return 3, normalized
    return 4, normalized
