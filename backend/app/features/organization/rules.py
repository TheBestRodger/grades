from __future__ import annotations

from typing import Protocol


class RoleLike(Protocol):
    system_role: str
    is_hr: bool


def has_hr_access(actor: RoleLike) -> bool:
    return actor.is_hr or actor.system_role == "hr"


def is_manager(actor: RoleLike) -> bool:
    return actor.system_role == "manager"


def is_employee(actor: RoleLike) -> bool:
    return actor.system_role == "employee"


def can_view_full_organization(actor: RoleLike) -> bool:
    return has_hr_access(actor)


def can_view_employee_only_scope(actor: RoleLike) -> bool:
    return is_employee(actor) and not has_hr_access(actor)


def effective_is_hr(system_role: str, is_hr: bool) -> bool:
    return is_hr or system_role == "hr"
