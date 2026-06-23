from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import Assignment, Employee, OrgUnit, StaffingLine


def load_active_employees(session: Session) -> list[Employee]:
    return session.scalars(
        select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.is_demo.desc(), Employee.id)
    ).all()


def load_active_employee(session: Session, employee_id: int) -> Employee | None:
    return session.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.is_active.is_(True),
        )
    )


def load_units(session: Session, *, is_demo: bool) -> list[OrgUnit]:
    return session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(is_demo))).all()


def load_units_with_parent(session: Session, *, is_demo: bool) -> list[OrgUnit]:
    return session.scalars(
        select(OrgUnit)
        .where(OrgUnit.is_demo.is_(is_demo))
        .options(selectinload(OrgUnit.parent))
    ).all()


def load_actor_assignments(
    session: Session,
    actor: Employee,
    *,
    is_demo: bool,
) -> list[Assignment]:
    return session.scalars(
        select(Assignment)
        .where(
            Assignment.employee_id == actor.id,
            Assignment.is_demo.is_(is_demo),
        )
        .options(selectinload(Assignment.staffing_line))
    ).all()


def load_manager_candidates_for_unit(
    session: Session,
    unit_id: int,
    *,
    is_demo: bool,
    exclude_employee_id: int | None = None,
) -> list[Assignment]:
    conditions = [
        StaffingLine.org_unit_id == unit_id,
        Assignment.is_demo.is_(is_demo),
        Employee.is_active.is_(True),
        Employee.system_role == "manager",
    ]
    if exclude_employee_id is not None:
        conditions.append(Employee.id != exclude_employee_id)
    return session.scalars(
        select(Assignment)
        .join(Assignment.employee)
        .join(Assignment.staffing_line)
        .where(*conditions)
        .options(
            selectinload(Assignment.employee),
            selectinload(Assignment.staffing_line).selectinload(StaffingLine.org_unit),
        )
    ).all()


def load_manager_assignments(session: Session, *, is_demo: bool) -> list[Assignment]:
    return session.scalars(
        select(Assignment)
        .join(Assignment.employee)
        .where(
            Assignment.is_demo.is_(is_demo),
            Employee.system_role == "manager",
        )
        .options(
            selectinload(Assignment.employee),
            selectinload(Assignment.staffing_line).selectinload(StaffingLine.org_unit),
        )
        .order_by(Assignment.id)
    ).all()


def load_staffing_lines_for_units(
    session: Session,
    unit_ids: set[int],
) -> list[StaffingLine]:
    return session.scalars(
        select(StaffingLine)
        .where(StaffingLine.org_unit_id.in_(unit_ids))
        .options(selectinload(StaffingLine.assignments).selectinload(Assignment.employee))
        .order_by(StaffingLine.title, StaffingLine.id)
    ).all()


def load_summary_lines(session: Session, unit_ids: set[int]) -> list[StaffingLine]:
    return session.scalars(
        select(StaffingLine)
        .where(StaffingLine.org_unit_id.in_(unit_ids))
        .options(selectinload(StaffingLine.assignments))
    ).all()
