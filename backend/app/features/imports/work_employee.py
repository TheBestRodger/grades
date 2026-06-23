from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import Assignment, Employee, StaffingLine
from .work_employee_audit import audit_work_employee_import
from .work_employee_errors import WorkEmployeeImportError
from .work_employee_managers import resolve_managers
from .work_employee_reader import read_rows
from .work_employee_upsert import upsert_people_and_assignments
from .work_employee_validation import (
    canonical_rows,
    normalize,
    normalize_path,
    prepare_rows,
    validate_fte_capacity,
    validate_people,
)


def import_work_assignments(
    session: Session,
    actor: Employee,
    filename: str,
    content: bytes,
) -> dict[str, object]:
    if not content:
        raise WorkEmployeeImportError("Файл импорта пуст.")
    source_name = Path(filename or "employees.csv").name
    rows = canonical_rows(read_rows(source_name, content))
    if not rows:
        raise WorkEmployeeImportError("В файле нет строк сотрудников.")

    lines = session.scalars(
        select(StaffingLine)
        .where(StaffingLine.is_demo.is_(False), StaffingLine.is_active.is_(True))
        .options(selectinload(StaffingLine.org_unit))
    ).all()
    line_by_key = {
        (normalize_path(line.org_unit.path), normalize(line.title)): line
        for line in lines
    }
    prepared = prepare_rows(rows, line_by_key)

    existing_assignments = _load_existing_assignments(session, prepared)
    _ensure_assignments_belong_to_work(existing_assignments)
    employees_by_external, employees_by_email = _load_existing_employees(session, prepared)
    validate_people(prepared, employees_by_external, employees_by_email)
    validate_fte_capacity(session, prepared, existing_assignments)

    stats = upsert_people_and_assignments(
        session,
        prepared,
        employees_by_external,
        existing_assignments,
    )
    assignments_by_external = stats.pop("assignments_by_external")
    resolve_managers(session, prepared, assignments_by_external)

    digest = sha256(content).hexdigest()
    audit_work_employee_import(session, actor, source_name, digest, len(prepared), stats)
    return {
        "scope": "work",
        "filename": source_name,
        "sha256": digest,
        "rows": len(prepared),
        **stats,
    }


def _load_existing_assignments(
    session: Session,
    rows: list[dict[str, object]],
) -> dict[str | None, Assignment]:
    external_ids = [row["assignment_id"] for row in rows]
    return {
        assignment.external_assignment_id: assignment
        for assignment in session.scalars(
            select(Assignment)
            .where(Assignment.external_assignment_id.in_(external_ids))
            .options(selectinload(Assignment.employee))
        ).all()
    }


def _ensure_assignments_belong_to_work(assignments: dict[str | None, Assignment]) -> None:
    for assignment_id, assignment in assignments.items():
        if assignment.is_demo:
            raise WorkEmployeeImportError(
                f"ID назначения {assignment_id} уже используется в другом контуре.",
                409,
            )


def _load_existing_employees(
    session: Session,
    rows: list[dict[str, object]],
) -> tuple[dict[str | None, Employee], dict[str, Employee]]:
    employee_ids = {row["employee_id"] for row in rows}
    emails = {row["email"] for row in rows}
    employees_by_external = {
        employee.external_employee_id: employee
        for employee in session.scalars(
            select(Employee).where(Employee.external_employee_id.in_(employee_ids))
        ).all()
    }
    employees_by_email = {
        employee.email: employee
        for employee in session.scalars(select(Employee).where(Employee.email.in_(emails))).all()
    }
    return employees_by_external, employees_by_email
