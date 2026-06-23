from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Assignment, Employee


def upsert_people_and_assignments(
    session: Session,
    rows: list[dict[str, object]],
    employees_by_external: dict[str | None, Employee],
    existing_assignments: dict[str | None, Assignment],
) -> dict[str, object]:
    stats: dict[str, object] = {
        "created_employees": 0,
        "updated_employees": 0,
        "created_assignments": 0,
        "updated_assignments": 0,
    }
    import_employees: dict[str, Employee] = {}
    assignments_by_external: dict[str, Assignment] = dict(existing_assignments)
    for row in rows:
        employee = _upsert_employee(session, row, employees_by_external, import_employees, stats)
        _upsert_assignment(session, row, employee, assignments_by_external, stats)
    stats["assignments_by_external"] = assignments_by_external
    return stats


def _upsert_employee(
    session: Session,
    row: dict[str, object],
    employees_by_external: dict[str | None, Employee],
    import_employees: dict[str, Employee],
    stats: dict[str, object],
) -> Employee:
    employee = import_employees.get(row["employee_id"]) or employees_by_external.get(
        row["employee_id"]
    )
    if employee is None:
        employee = Employee(
            external_employee_id=row["employee_id"],
            full_name=row["full_name"],
            email=row["email"],
            username=str(row["email"]).strip().lower(),
            system_role=row["role"],
            is_demo=False,
            is_active=True,
        )
        session.add(employee)
        session.flush()
        stats["created_employees"] = int(stats["created_employees"]) + 1
    elif row["employee_id"] not in import_employees:
        employee.full_name = row["full_name"]
        employee.email = row["email"]
        employee.username = str(row["email"]).strip().lower()
        employee.system_role = row["role"]
        employee.is_active = True
        stats["updated_employees"] = int(stats["updated_employees"]) + 1
    import_employees[str(row["employee_id"])] = employee
    return employee


def _upsert_assignment(
    session: Session,
    row: dict[str, object],
    employee: Employee,
    assignments_by_external: dict[str, Assignment],
    stats: dict[str, object],
) -> None:
    assignment = assignments_by_external.get(row["assignment_id"])
    if assignment is None:
        assignment = Assignment(
            external_assignment_id=row["assignment_id"],
            employee=employee,
            staffing_line=row["line"],
            fte=row["fte"],
            assignment_role="primary",
            is_demo=False,
        )
        session.add(assignment)
        session.flush()
        assignments_by_external[str(row["assignment_id"])] = assignment
        stats["created_assignments"] = int(stats["created_assignments"]) + 1
        return
    assignment.employee = employee
    assignment.staffing_line = row["line"]
    assignment.fte = row["fte"]
    assignment.is_demo = False
    stats["updated_assignments"] = int(stats["updated_assignments"]) + 1
