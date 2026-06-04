from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Assignment, Employee, OrgUnit, StaffingLine


def get_demo_users(session: Session) -> list[dict[str, object]]:
    users = session.scalars(
        select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.is_demo.desc(), Employee.id)
    ).all()
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "username": user.username,
            "role": user.system_role,
            "is_demo": user.is_demo,
        }
        for user in users
    ]


def require_actor(session: Session, employee_id: int) -> Employee | None:
    return session.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.is_active.is_(True),
        )
    )


def _unit_descendants(units: list[OrgUnit], root_ids: set[int]) -> set[int]:
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


def _visible_unit_ids(session: Session, actor: Employee, is_demo: bool = True) -> set[int]:
    units = session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(is_demo))).all()
    if actor.system_role == "hr":
        return {unit.id for unit in units}
    assignment_units = {
        assignment.staffing_line.org_unit_id
        for assignment in session.scalars(
            select(Assignment)
            .where(
                Assignment.employee_id == actor.id,
                Assignment.is_demo.is_(is_demo),
            )
            .options(selectinload(Assignment.staffing_line))
        ).all()
    }
    if actor.system_role == "manager":
        return _unit_descendants(units, assignment_units)
    return assignment_units


def _assigned_fte(line: StaffingLine) -> float:
    assigned_from_people = round(sum(assignment.fte for assignment in line.assignments), 2)
    if not line.is_demo and line.reported_occupied_fte:
        return round(line.reported_occupied_fte, 2)
    if assigned_from_people:
        return assigned_from_people
    return round(line.reported_occupied_fte, 2)


def organization_tree(session: Session, actor: Employee, is_demo: bool = True) -> dict[str, object]:
    visible_unit_ids = _visible_unit_ids(session, actor, is_demo)
    if not visible_unit_ids:
        return {"scope": "demo" if is_demo else "work", "nodes": []}
    units = session.scalars(
        select(OrgUnit)
        .where(OrgUnit.id.in_(visible_unit_ids))
        .order_by(OrgUnit.name, OrgUnit.id)
    ).all()

    lines = session.scalars(
        select(StaffingLine)
        .where(StaffingLine.org_unit_id.in_(visible_unit_ids))
        .options(selectinload(StaffingLine.assignments).selectinload(Assignment.employee))
        .order_by(StaffingLine.title, StaffingLine.id)
    ).all()
    if actor.system_role == "employee":
        lines = [
            line
            for line in lines
            if any(assignment.employee_id == actor.id for assignment in line.assignments)
        ]

    line_map: dict[int, list[dict[str, object]]] = defaultdict(list)
    for line in lines:
        assignments = sorted(line.assignments, key=lambda assignment: assignment.employee.full_name)
        if actor.system_role == "employee":
            assignments = [
                assignment for assignment in assignments if assignment.employee_id == actor.id
            ]
        assigned_fte = _assigned_fte(line)
        line_map[line.org_unit_id].append(
            {
                "id": line.id,
                "title": line.title,
                "position_code": line.position_code,
                "approved_fte": line.approved_fte if actor.system_role != "employee" else None,
                "assigned_fte": assigned_fte if actor.system_role != "employee" else None,
                "vacancy_fte": (
                    round(line.approved_fte - assigned_fte, 2)
                    if actor.system_role != "employee"
                    else None
                ),
                "assignments": [
                    {
                        "id": assignment.id,
                        "employee_id": assignment.employee_id,
                        "employee_name": assignment.employee.full_name,
                        "fte": assignment.fte,
                        "role": assignment.employee.system_role,
                    }
                    for assignment in assignments
                ],
            }
        )

    children_map: dict[int | None, list[OrgUnit]] = defaultdict(list)
    for unit in units:
        parent_id = unit.parent_id if unit.parent_id in visible_unit_ids else None
        children_map[parent_id].append(unit)

    def node(unit: OrgUnit) -> dict[str, object]:
        return {
            "id": unit.id,
            "name": unit.name,
            "department_code": unit.department_code,
            "is_demo": unit.is_demo,
            "positions": sorted(line_map.get(unit.id, []), key=lambda position: str(position["title"])),
            "children": [node(child) for child in sorted(children_map.get(unit.id, []), key=lambda item: item.name)],
        }

    return {
        "scope": actor.system_role if is_demo else "work",
        "nodes": [node(root) for root in sorted(children_map[None], key=lambda item: item.name)],
    }


def organization_summary(session: Session, actor: Employee, is_demo: bool = True) -> dict[str, object]:
    if actor.system_role == "employee" and is_demo:
        return {
            "scope": "self",
            "employees": 1,
            "staffing_lines": None,
            "approved_fte": None,
            "assigned_fte": None,
            "vacancy_fte": None,
        }

    visible_unit_ids = _visible_unit_ids(session, actor, is_demo)
    if not visible_unit_ids:
        return {
            "scope": "work" if not is_demo else actor.system_role,
            "employees": 0,
            "staffing_lines": 0,
            "approved_fte": 0,
            "assigned_fte": 0,
            "vacancy_fte": 0,
        }
    lines = session.scalars(
        select(StaffingLine)
        .where(StaffingLine.org_unit_id.in_(visible_unit_ids))
        .options(selectinload(StaffingLine.assignments))
    ).all()
    employees = {
        assignment.employee_id for line in lines for assignment in line.assignments
    }
    approved = round(sum(line.approved_fte for line in lines), 2)
    assigned = round(sum(_assigned_fte(line) for line in lines), 2)
    return {
        "scope": actor.system_role if is_demo else "work",
        "employees": len(employees),
        "staffing_lines": len(lines),
        "approved_fte": approved,
        "assigned_fte": assigned,
        "vacancy_fte": round(approved - assigned, 2),
    }
