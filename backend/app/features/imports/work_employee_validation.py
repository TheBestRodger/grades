from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Assignment, Employee, StaffingLine
from .work_employee_errors import WorkEmployeeImportError


HEADER_ALIASES = {
    "assignment_id": {"id назначения", "assignment_id", "assignment id"},
    "employee_id": {"id сотрудника", "employee_id", "employee id"},
    "full_name": {"фио", "full_name", "full name"},
    "email": {"email", "e-mail"},
    "unit_path": {"путь подразделения", "org_unit_path", "unit_path", "подразделение"},
    "position_title": {"должность", "position_title", "position"},
    "fte": {"ставка", "fte"},
    "manager_assignment_id": {
        "id назначения руководителя",
        "manager_assignment_id",
        "manager assignment id",
    },
    "role": {"роль", "system_role", "role"},
}
REQUIRED_FIELDS = {
    "assignment_id",
    "employee_id",
    "full_name",
    "email",
    "unit_path",
    "position_title",
    "fte",
}


def canonical_rows(raw_rows: list[dict[str, object]]) -> list[dict[str, str]]:
    if not raw_rows:
        return []
    header_map: dict[str, str] = {}
    for source_header in raw_rows[0]:
        normalized = normalize(source_header).lower()
        for key, aliases in HEADER_ALIASES.items():
            if normalized in aliases:
                header_map[source_header] = key
                break
    missing = sorted(REQUIRED_FIELDS - set(header_map.values()))
    if missing:
        raise WorkEmployeeImportError(
            "Не хватает обязательных колонок: " + ", ".join(missing) + "."
        )
    return [
        {target: normalize(row.get(source, "")) for source, target in header_map.items()}
        for row in raw_rows
        if any(normalize(value) for value in row.values())
    ]


def prepare_rows(
    rows: list[dict[str, str]],
    line_by_key: dict[tuple[str, str], StaffingLine],
) -> list[dict[str, object]]:
    prepared: list[dict[str, object]] = []
    seen_assignments: set[str] = set()
    for index, row in enumerate(rows, start=2):
        assignment_id = row.get("assignment_id", "")
        employee_id = row.get("employee_id", "")
        full_name = " ".join(row.get("full_name", "").split())
        email = row.get("email", "").strip().lower()
        role = row.get("role", "employee").strip().lower() or "employee"
        _validate_basic_row(index, assignment_id, employee_id, full_name, email, role)
        seen_assignments = _ensure_unique_assignment(index, assignment_id, seen_assignments)
        fte = _parse_fte(index, row.get("fte", "0"))
        line = line_by_key.get(
            (normalize_path(row.get("unit_path", "")), normalize(row.get("position_title", "")))
        )
        if line is None:
            raise WorkEmployeeImportError(
                f"Строка {index}: штатная позиция не найдена в рабочем ШР."
            )
        prepared.append(
            {
                "assignment_id": assignment_id,
                "employee_id": employee_id,
                "full_name": full_name,
                "email": email,
                "role": role,
                "fte": fte,
                "manager_assignment_id": row.get("manager_assignment_id", ""),
                "line": line,
            }
        )
    return prepared


def validate_people(
    rows: list[dict[str, object]],
    employees_by_external: dict[str | None, Employee],
    employees_by_email: dict[str, Employee],
) -> None:
    values_by_employee: dict[str, tuple[str, str, str]] = {}
    for row in rows:
        external_id = str(row["employee_id"])
        expected = (str(row["full_name"]), str(row["email"]), str(row["role"]))
        previous = values_by_employee.setdefault(external_id, expected)
        if previous != expected:
            raise WorkEmployeeImportError(
                f"Сотрудник {external_id} указан с разными ФИО, email или ролями."
            )
        existing_by_id = employees_by_external.get(external_id)
        existing_by_email = employees_by_email.get(str(row["email"]))
        if existing_by_id is not None and existing_by_id.is_demo:
            raise WorkEmployeeImportError(
                f"ID сотрудника {external_id} уже используется в другом контуре.",
                409,
            )
        if existing_by_email is not None and existing_by_email is not existing_by_id:
            raise WorkEmployeeImportError(
                f"Email {row['email']} уже принадлежит другому сотруднику.",
                409,
            )


def validate_fte_capacity(
    session: Session,
    rows: list[dict[str, object]],
    existing_assignments: dict[str | None, Assignment],
) -> None:
    line_ids = {row["line"].id for row in rows}
    totals = defaultdict(float)
    for assignment in session.scalars(
        select(Assignment).where(
            Assignment.staffing_line_id.in_(line_ids),
            Assignment.is_demo.is_(False),
        )
    ).all():
        totals[assignment.staffing_line_id] += assignment.fte
    for row in rows:
        existing = existing_assignments.get(str(row["assignment_id"]))
        if existing is not None:
            totals[existing.staffing_line_id] -= existing.fte
        totals[row["line"].id] += float(row["fte"])
    for row in rows:
        line = row["line"]
        if totals[line.id] > line.approved_fte + 1e-9:
            raise WorkEmployeeImportError(
                f"Позиция «{line.title}» превышает ставки по ШР после импорта.",
                409,
            )


def normalize(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def normalize_path(value: object) -> str:
    text = normalize(value).replace("\\", "/").strip("/")
    return text[5:] if text.upper().startswith("WORK/") else text


def _validate_basic_row(
    index: int,
    assignment_id: str,
    employee_id: str,
    full_name: str,
    email: str,
    role: str,
) -> None:
    if not assignment_id or not employee_id or len(full_name) < 3:
        raise WorkEmployeeImportError(f"Строка {index}: не заполнены идентификаторы или ФИО.")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise WorkEmployeeImportError(f"Строка {index}: некорректный email.")
    if role not in {"employee", "manager"}:
        raise WorkEmployeeImportError(f"Строка {index}: роль должна быть employee или manager.")


def _ensure_unique_assignment(index: int, assignment_id: str, seen: set[str]) -> set[str]:
    if assignment_id in seen:
        raise WorkEmployeeImportError(f"Строка {index}: повторяется ID назначения {assignment_id}.")
    seen.add(assignment_id)
    return seen


def _parse_fte(index: int, value: str) -> float:
    try:
        fte = float(value.replace(",", "."))
    except ValueError as exc:
        raise WorkEmployeeImportError(f"Строка {index}: ставка должна быть числом.") from exc
    if fte <= 0 or fte > 10:
        raise WorkEmployeeImportError(f"Строка {index}: некорректная ставка.")
    return fte
