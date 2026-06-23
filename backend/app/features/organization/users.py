from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Employee
from . import repository
from .rules import effective_is_hr


def get_demo_users(session: Session) -> list[dict[str, object]]:
    users = repository.load_active_employees(session)
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "username": user.username,
            "role": user.system_role,
            "is_hr": effective_is_hr(user.system_role, user.is_hr),
            "is_demo": user.is_demo,
        }
        for user in users
    ]


def require_actor(session: Session, employee_id: int) -> Employee | None:
    return repository.load_active_employee(session, employee_id)
