from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from ...features.auth.passwords import generate_temporary_password, hash_password
from ...models import Employee
from . import repository
from .audit import audit
from .errors import StructureOperationError


def login_from_email(email: str) -> str:
    return email.strip().lower()


def archive_employee_email(employee: Employee, archived_at: datetime) -> str:
    timestamp_ms = int(archived_at.timestamp() * 1000)
    email_prefix, _, email_domain = employee.email.partition("@")
    safe_prefix = re.sub(r"[^a-z0-9_.+-]+", ".", email_prefix.strip().lower()) or "archived"
    safe_domain = re.sub(r"[^a-z0-9_.-]+", ".", email_domain.strip().lower()) or "archived.local"
    return f"{safe_prefix}+deleted-{employee.id}-{timestamp_ms}@{safe_domain}"


def reset_employee_password(
    session: Session,
    actor: Employee,
    assignment_id: int,
    *,
    is_demo: bool = True,
) -> dict[str, object]:
    assignment = repository.load_assignment(session, assignment_id, is_demo=is_demo)
    if assignment is None:
        raise StructureOperationError("Назначение не найдено.", 404)

    employee = assignment.employee
    employee.username = login_from_email(employee.email)
    temporary_password = generate_temporary_password()
    employee.password_hash = hash_password(temporary_password)
    session.flush()
    audit(
        session,
        actor,
        "employee.password_reset",
        "assignment",
        assignment.id,
        {
            "scope": "demo" if is_demo else "work",
            "assignment_id": assignment.id,
            "employee_id": employee.id,
            "full_name": employee.full_name,
            "email": employee.email,
            "username": employee.username,
            "staffing_title": assignment.staffing_line.title,
            "unit_name": assignment.staffing_line.org_unit.name,
        },
    )
    return {
        "assignment_id": assignment.id,
        "employee_id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "username": employee.username,
        "password": temporary_password,
        "staffing_line_id": assignment.staffing_line_id,
        "staffing_title": assignment.staffing_line.title,
        "unit_name": assignment.staffing_line.org_unit.name,
    }


_archive_employee_email = archive_employee_email
