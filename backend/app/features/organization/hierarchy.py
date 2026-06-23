from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from ...models import Employee, OrgUnit, StaffingLine
from . import repository
from .rules import can_view_full_organization, is_manager


def unit_descendants(units: list[OrgUnit], root_ids: set[int]) -> set[int]:
    children: dict[int | None, list[int]] = defaultdict(list)
    for unit in units:
        children[unit.parent_id].append(unit.id)
    visible: set[int] = set()
    pending = list(root_ids)
    while pending:
        current = pending.pop()
        if current in visible:
            continue
        visible.add(current)
        pending.extend(children[current])
    return visible


def visible_unit_ids(session: Session, actor: Employee, is_demo: bool = True) -> set[int]:
    units = repository.load_units(session, is_demo=is_demo)
    if can_view_full_organization(actor):
        return {unit.id for unit in units}
    assignment_units = {
        assignment.staffing_line.org_unit_id
        for assignment in repository.load_actor_assignments(session, actor, is_demo=is_demo)
    }
    if is_manager(actor):
        return unit_descendants(units, assignment_units)
    return assignment_units


def assigned_fte(line: StaffingLine) -> float:
    return round(sum(assignment.fte for assignment in line.assignments), 2)


_unit_descendants = unit_descendants
_visible_unit_ids = visible_unit_ids
_assigned_fte = assigned_fte
