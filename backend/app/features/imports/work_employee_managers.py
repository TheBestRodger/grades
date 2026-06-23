from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Assignment
from ..organization.service import resolve_manager_assignment_for_line
from .work_employee_errors import WorkEmployeeImportError


def resolve_managers(
    session: Session,
    rows: list[dict[str, object]],
    assignments_by_external: dict[str, Assignment],
) -> None:
    manager_ids = {row["manager_assignment_id"] for row in rows if row["manager_assignment_id"]}
    _load_missing_managers(session, manager_ids, assignments_by_external)
    unresolved = {str(item) for item in manager_ids} - set(assignments_by_external)
    if unresolved:
        raise WorkEmployeeImportError(
            "Не найдены назначения руководителей: " + ", ".join(sorted(unresolved)) + "."
        )
    for row in rows:
        assignment = assignments_by_external[str(row["assignment_id"])]
        manager_id = row["manager_assignment_id"]
        manager = assignments_by_external.get(str(manager_id)) if manager_id else None
        if manager is assignment:
            raise WorkEmployeeImportError(
                f"Назначение {row['assignment_id']} не может быть руководителем само себе."
            )
        assignment.manager = manager
    _fill_missing_managers(session, rows, assignments_by_external)


def _load_missing_managers(
    session: Session,
    manager_ids: set[object],
    assignments_by_external: dict[str, Assignment],
) -> None:
    missing_manager_ids = {str(item) for item in manager_ids} - set(assignments_by_external)
    if not missing_manager_ids:
        return
    database_managers = session.scalars(
        select(Assignment).where(
            Assignment.external_assignment_id.in_(missing_manager_ids),
            Assignment.is_demo.is_(False),
        )
    ).all()
    assignments_by_external.update(
        {str(assignment.external_assignment_id): assignment for assignment in database_managers}
    )


def _fill_missing_managers(
    session: Session,
    rows: list[dict[str, object]],
    assignments_by_external: dict[str, Assignment],
) -> None:
    for row in rows:
        if row["manager_assignment_id"]:
            continue
        assignment = assignments_by_external[str(row["assignment_id"])]
        if assignment.manager is not None:
            continue
        resolved_manager = resolve_manager_assignment_for_line(session, assignment.staffing_line)
        if resolved_manager is not None and resolved_manager is not assignment:
            assignment.manager = resolved_manager
