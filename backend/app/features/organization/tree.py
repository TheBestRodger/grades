from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from ...models import Employee, OrgUnit, StaffingLine
from . import repository
from .hierarchy import assigned_fte, visible_unit_ids
from .rules import can_view_employee_only_scope, has_hr_access


def organization_tree(session: Session, actor: Employee, is_demo: bool = True) -> dict[str, object]:
    unit_ids = visible_unit_ids(session, actor, is_demo)
    if not unit_ids:
        return {"scope": "demo" if is_demo else "work", "nodes": []}

    units = _visible_units(session, unit_ids, is_demo=is_demo)
    lines = _visible_lines(session, actor, unit_ids)
    line_map = _line_map(actor, lines)
    children_map = _children_map(units, unit_ids)

    return {
        "scope": actor.system_role if is_demo else "work",
        "nodes": [
            _node(root, line_map, children_map)
            for root in sorted(children_map[None], key=lambda item: item.name)
        ],
    }


def _visible_units(session: Session, unit_ids: set[int], *, is_demo: bool) -> list[OrgUnit]:
    return sorted(
        [unit for unit in repository.load_units(session, is_demo=is_demo) if unit.id in unit_ids],
        key=lambda unit: (unit.name, unit.id),
    )


def _visible_lines(session: Session, actor: Employee, unit_ids: set[int]) -> list[StaffingLine]:
    lines = repository.load_staffing_lines_for_units(session, unit_ids)
    if not can_view_employee_only_scope(actor):
        return lines
    return [
        line
        for line in lines
        if any(assignment.employee_id == actor.id for assignment in line.assignments)
    ]


def _line_map(actor: Employee, lines: list[StaffingLine]) -> dict[int, list[dict[str, object]]]:
    line_map: dict[int, list[dict[str, object]]] = defaultdict(list)
    for line in lines:
        assignments = sorted(line.assignments, key=lambda assignment: assignment.employee.full_name)
        if can_view_employee_only_scope(actor):
            assignments = [
                assignment for assignment in assignments if assignment.employee_id == actor.id
            ]
        can_see_staffing = not can_view_employee_only_scope(actor)
        line_map[line.org_unit_id].append(_line_payload(line, assignments, can_see_staffing))
    return line_map


def _line_payload(line: StaffingLine, assignments: list[object], can_see_staffing: bool) -> dict[str, object]:
    line_assigned_fte = assigned_fte(line)
    return {
        "id": line.id,
        "title": line.title,
        "position_code": line.position_code,
        "approved_fte": line.approved_fte if can_see_staffing else None,
        "assigned_fte": line_assigned_fte if can_see_staffing else None,
        "vacancy_fte": round(line.approved_fte - line_assigned_fte, 2) if can_see_staffing else None,
        "assignments": [
            {
                "id": assignment.id,
                "employee_id": assignment.employee_id,
                "employee_name": assignment.employee.full_name,
                "employee_email": assignment.employee.email,
                "fte": assignment.fte,
                "role": assignment.employee.system_role,
                "is_hr": has_hr_access(assignment.employee),
            }
            for assignment in assignments
        ],
    }


def _children_map(units: list[OrgUnit], unit_ids: set[int]) -> dict[int | None, list[OrgUnit]]:
    children_map: dict[int | None, list[OrgUnit]] = defaultdict(list)
    for unit in units:
        parent_id = unit.parent_id if unit.parent_id in unit_ids else None
        children_map[parent_id].append(unit)
    return children_map


def _node(
    unit: OrgUnit,
    line_map: dict[int, list[dict[str, object]]],
    children_map: dict[int | None, list[OrgUnit]],
) -> dict[str, object]:
    return {
        "id": unit.id,
        "name": unit.name,
        "department_code": unit.department_code,
        "is_demo": unit.is_demo,
        "positions": sorted(line_map.get(unit.id, []), key=lambda position: str(position["title"])),
        "children": [
            _node(child, line_map, children_map)
            for child in sorted(children_map.get(unit.id, []), key=lambda item: item.name)
        ],
    }
