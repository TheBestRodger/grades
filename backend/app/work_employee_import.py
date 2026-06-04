from __future__ import annotations

import csv
from collections import defaultdict
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Assignment, AuditEvent, Employee, OrgUnit, StaffingLine


NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
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


class WorkEmployeeImportError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def import_work_assignments(
    session: Session,
    actor: Employee,
    filename: str,
    content: bytes,
) -> dict[str, object]:
    if not content:
        raise WorkEmployeeImportError("Файл импорта пуст.")
    source_name = Path(filename or "employees.csv").name
    raw_rows = _read_rows(source_name, content)
    rows = _canonical_rows(raw_rows)
    if not rows:
        raise WorkEmployeeImportError("В файле нет строк сотрудников.")

    lines = session.scalars(
        select(StaffingLine)
        .where(StaffingLine.is_demo.is_(False), StaffingLine.is_active.is_(True))
        .options(selectinload(StaffingLine.org_unit))
    ).all()
    line_by_key = {
        (_normalize_path(line.org_unit.path), _normalize(line.title)): line
        for line in lines
    }
    prepared = _prepare_rows(rows, line_by_key)

    external_assignment_ids = [row["assignment_id"] for row in prepared]
    existing_assignments = {
        assignment.external_assignment_id: assignment
        for assignment in session.scalars(
            select(Assignment)
            .where(Assignment.external_assignment_id.in_(external_assignment_ids))
            .options(selectinload(Assignment.employee))
        ).all()
    }
    for assignment_id, assignment in existing_assignments.items():
        if assignment.is_demo:
            raise WorkEmployeeImportError(
                f"ID назначения {assignment_id} уже используется в другом контуре.",
                409,
            )

    employee_ids = {row["employee_id"] for row in prepared}
    employees_by_external = {
        employee.external_employee_id: employee
        for employee in session.scalars(
            select(Employee).where(Employee.external_employee_id.in_(employee_ids))
        ).all()
    }
    emails = {row["email"] for row in prepared}
    employees_by_email = {
        employee.email: employee
        for employee in session.scalars(select(Employee).where(Employee.email.in_(emails))).all()
    }

    _validate_people(prepared, employees_by_external, employees_by_email)
    _validate_fte_capacity(session, prepared, existing_assignments)

    created_employees = 0
    updated_employees = 0
    created_assignments = 0
    updated_assignments = 0
    import_employees: dict[str, Employee] = {}
    assignments_by_external: dict[str, Assignment] = dict(existing_assignments)

    for row in prepared:
        employee = import_employees.get(row["employee_id"]) or employees_by_external.get(
            row["employee_id"]
        )
        if employee is None:
            employee = Employee(
                external_employee_id=row["employee_id"],
                full_name=row["full_name"],
                email=row["email"],
                system_role=row["role"],
                is_demo=False,
                is_active=True,
            )
            session.add(employee)
            session.flush()
            created_employees += 1
        elif row["employee_id"] not in import_employees:
            employee.full_name = row["full_name"]
            employee.email = row["email"]
            employee.system_role = row["role"]
            employee.is_active = True
            updated_employees += 1
        import_employees[row["employee_id"]] = employee

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
            assignments_by_external[row["assignment_id"]] = assignment
            created_assignments += 1
        else:
            assignment.employee = employee
            assignment.staffing_line = row["line"]
            assignment.fte = row["fte"]
            assignment.is_demo = False
            updated_assignments += 1

    manager_ids = {
        row["manager_assignment_id"]
        for row in prepared
        if row["manager_assignment_id"]
    }
    missing_manager_ids = manager_ids - set(assignments_by_external)
    if missing_manager_ids:
        database_managers = session.scalars(
            select(Assignment).where(
                Assignment.external_assignment_id.in_(missing_manager_ids),
                Assignment.is_demo.is_(False),
            )
        ).all()
        assignments_by_external.update(
            {assignment.external_assignment_id: assignment for assignment in database_managers}
        )
    unresolved = manager_ids - set(assignments_by_external)
    if unresolved:
        raise WorkEmployeeImportError(
            "Не найдены назначения руководителей: " + ", ".join(sorted(unresolved)) + "."
        )
    for row in prepared:
        assignment = assignments_by_external[row["assignment_id"]]
        manager_id = row["manager_assignment_id"]
        manager = assignments_by_external.get(manager_id) if manager_id else None
        if manager is assignment:
            raise WorkEmployeeImportError(
                f"Назначение {row['assignment_id']} не может быть руководителем само себе."
            )
        assignment.manager = manager

    digest = sha256(content).hexdigest()
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="employees.work_imported",
            entity_type="employee_import",
            entity_id=digest[:16],
            details_json=json.dumps(
                {
                    "scope": "work",
                    "filename": source_name,
                    "sha256": digest,
                    "rows": len(prepared),
                    "created_employees": created_employees,
                    "updated_employees": updated_employees,
                    "created_assignments": created_assignments,
                    "updated_assignments": updated_assignments,
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return {
        "scope": "work",
        "filename": source_name,
        "sha256": digest,
        "rows": len(prepared),
        "created_employees": created_employees,
        "updated_employees": updated_employees,
        "created_assignments": created_assignments,
        "updated_assignments": updated_assignments,
    }


def _canonical_rows(raw_rows: list[dict[str, object]]) -> list[dict[str, str]]:
    if not raw_rows:
        return []
    header_map: dict[str, str] = {}
    for source_header in raw_rows[0]:
        normalized = _normalize(source_header).lower()
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
        {
            target: _normalize(row.get(source, ""))
            for source, target in header_map.items()
        }
        for row in raw_rows
        if any(_normalize(value) for value in row.values())
    ]


def _prepare_rows(
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
        if not assignment_id or not employee_id or len(full_name) < 3:
            raise WorkEmployeeImportError(f"Строка {index}: не заполнены идентификаторы или ФИО.")
        if assignment_id in seen_assignments:
            raise WorkEmployeeImportError(f"Строка {index}: повторяется ID назначения {assignment_id}.")
        seen_assignments.add(assignment_id)
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise WorkEmployeeImportError(f"Строка {index}: некорректный email.")
        if role not in {"employee", "manager"}:
            raise WorkEmployeeImportError(f"Строка {index}: роль должна быть employee или manager.")
        try:
            fte = float(row.get("fte", "0").replace(",", "."))
        except ValueError as exc:
            raise WorkEmployeeImportError(f"Строка {index}: ставка должна быть числом.") from exc
        if fte <= 0 or fte > 10:
            raise WorkEmployeeImportError(f"Строка {index}: некорректная ставка.")
        line = line_by_key.get(
            (_normalize_path(row.get("unit_path", "")), _normalize(row.get("position_title", "")))
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


def _validate_people(
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


def _validate_fte_capacity(
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


def _read_rows(filename: str, content: bytes) -> list[dict[str, object]]:
    if filename.lower().endswith(".xlsx"):
        return _read_xlsx_rows(content)
    if filename.lower().endswith(".csv"):
        return _read_csv_rows(content)
    raise WorkEmployeeImportError("Поддерживаются только файлы CSV и XLSX.")


def _read_csv_rows(content: bytes) -> list[dict[str, object]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise WorkEmployeeImportError("CSV должен быть в кодировке UTF-8.") from exc
    try:
        delimiter = csv.Sniffer().sniff(text[:2048], delimiters=";,").delimiter
    except csv.Error:
        delimiter = ";"
    return [dict(row) for row in csv.DictReader(StringIO(text), delimiter=delimiter)]


def _read_xlsx_rows(content: bytes) -> list[dict[str, object]]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            shared_strings = _shared_strings(archive)
            root = ET.fromstring(archive.read(_first_sheet_name(archive)))
    except (BadZipFile, KeyError, ET.ParseError, ValueError) as exc:
        raise WorkEmployeeImportError("Не удалось прочитать XLSX-файл.") from exc
    values: list[list[str]] = []
    for row in root.findall(".//a:sheetData/a:row", NS):
        row_values: list[str] = []
        for cell in row.findall("a:c", NS):
            index = _column_index(cell.attrib.get("r", ""))
            while len(row_values) < index:
                row_values.append("")
            row_values.append(_cell_value(cell, shared_strings))
        values.append(row_values)
    if not values:
        return []
    headers = values[0]
    return [
        {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        for row in values[1:]
    ]


def _first_sheet_name(archive: ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    first_sheet = workbook.find(".//a:sheets/a:sheet", NS)
    if first_sheet is None:
        raise ValueError("Workbook has no sheets.")
    rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
    rel = rels.find(
        f".//{{http://schemas.openxmlformats.org/package/2006/relationships}}Relationship[@Id='{rel_id}']"
    )
    if rel is None:
        raise ValueError("Workbook sheet relationship is missing.")
    target = rel.attrib["Target"].lstrip("/")
    return target if target.startswith("xl/") else f"xl/{target}"


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(text.text or "" for text in item.findall(".//a:t", NS))
        for item in root.findall("a:si", NS)
    ]


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", NS))
    value = cell.find("a:v", NS)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text


def _column_index(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha())
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter.upper()) - ord("A") + 1
    return max(result - 1, 0)


def _normalize(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _normalize_path(value: object) -> str:
    text = _normalize(value).replace("\\", "/").strip("/")
    return text[5:] if text.upper().startswith("WORK/") else text
