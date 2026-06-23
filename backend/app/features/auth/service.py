from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ...core.config import Settings
from ...models import Employee
from ..organization.rules import effective_is_hr
from . import email, magic_links, repository, sessions
from .errors import AuthOperationError
from .passwords import (
    PASSWORD_HASH_ALGORITHM,
    PASSWORD_HASH_ITERATIONS,
    TEMP_PASSWORD_ALPHABET,
    generate_temporary_password,
    hash_password,
    issue_temporary_password,
    normalize_login_from_email,
    username_from_name,
    verify_password,
)
from .magic_links import MAGIC_LINK_TTL_MINUTES
from .sessions import SESSION_TTL_HOURS


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def employee_payload(employee: Employee) -> dict[str, object]:
    return {
        "id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "username": employee.username,
        "role": employee.system_role,
        "is_hr": effective_is_hr(employee.system_role, employee.is_hr),
        "is_demo": employee.is_demo,
    }


def ensure_bootstrap_hr_credentials(session: Session, settings: Settings) -> None:
    if not settings.bootstrap_hr_username or not settings.bootstrap_hr_password:
        return
    hr = repository.find_bootstrap_hr(session)
    if hr is None:
        return
    hr.username = normalize_login_from_email(hr.email)
    hr.password_hash = hash_password(settings.bootstrap_hr_password)


def login_with_password(session: Session, username: str, password: str) -> dict[str, object]:
    normalized = username.strip().lower()
    employee = repository.find_active_employee_by_login(session, normalized)
    if employee is None or not verify_password(password, employee.password_hash):
        raise AuthOperationError("Неверный логин или пароль.", 401)

    now = _now()
    if employee.first_login_at is None:
        employee.first_login_at = now
    employee.last_login_at = now
    session_token, expires_at = sessions.issue_session(session, employee, now=now)
    repository.audit(
        session,
        employee.id,
        "auth.password_login",
        "employee",
        employee.id,
        {"session_ttl_hours": SESSION_TTL_HOURS, "is_demo": employee.is_demo},
    )
    return {
        "token": session_token,
        "expires_at": expires_at.isoformat(),
        "user": employee_payload(employee),
    }


def request_magic_link(session: Session, user_email: str, settings: Settings) -> dict[str, object]:
    normalized = user_email.strip().lower()
    employee = repository.find_active_employee_by_email(session, normalized)
    expires_at = magic_links.magic_link_expires_at(_now())
    response: dict[str, object] = {
        "email": normalized,
        "delivery_mode": "local_link" if settings.app_env in {"demo-local", "test"} else "email",
        "expires_at": expires_at.isoformat(),
        "login_token": None,
        "login_url": None,
        "message": "Будет выпущена одноразовая ссылка входа.",
    }
    if employee is None:
        repository.audit(
            session,
            None,
            "auth.magic_link_requested_unknown",
            "auth",
            "unknown",
            {"delivery_mode": response["delivery_mode"]},
        )
        raise AuthOperationError("Пользователь с таким email не найден.", 404)

    token = magic_links.issue_magic_link_token(session, employee, expires_at=expires_at)
    repository.audit(
        session,
        employee.id,
        "auth.magic_link_requested",
        "employee",
        employee.id,
        {"is_demo": employee.is_demo, "delivery_mode": response["delivery_mode"]},
    )
    login_url = f"{settings.public_base_url}/?auth_token={token}"
    if settings.app_env in {"demo-local", "test"}:
        response["login_token"] = token
        response["login_url"] = f"/?auth_token={token}"
        response["message"] = "Локальная одноразовая ссылка создана. В пилоте вместо показа ссылки будет отправка письма."
    else:
        email.send_magic_link_email(settings, employee.email, login_url)
        response["message"] = "Одноразовая ссылка отправлена на email."
    return response


def consume_magic_link(session: Session, token: str) -> dict[str, object]:
    now = _now()
    login_token = magic_links.load_valid_magic_link(session, token, now=now)

    if login_token.employee.first_login_at is None:
        login_token.employee.first_login_at = now
    login_token.employee.last_login_at = now
    session_token, expires_at = sessions.issue_session(session, login_token.employee, now=now)
    login_token.consumed_at = now
    repository.audit(
        session,
        login_token.employee_id,
        "auth.magic_link_consumed",
        "employee",
        login_token.employee_id,
        {"session_ttl_hours": SESSION_TTL_HOURS, "is_demo": login_token.employee.is_demo},
    )
    return {
        "token": session_token,
        "expires_at": expires_at.isoformat(),
        "user": employee_payload(login_token.employee),
    }


def actor_from_authorization(session: Session, authorization: str | None) -> Employee | None:
    return sessions.actor_from_authorization(session, authorization, now=_now())


def logout_session(session: Session, authorization: str | None) -> dict[str, object]:
    return sessions.logout_session(session, authorization, now=_now())
