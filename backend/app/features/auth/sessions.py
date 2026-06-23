from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ...models import Employee
from .errors import AuthOperationError
from .magic_links import hash_token, new_token
from . import repository

SESSION_TTL_HOURS = 8


def issue_session(
    session: Session,
    employee: Employee,
    *,
    now: datetime,
) -> tuple[str, datetime]:
    session_token = new_token()
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
    repository.add_auth_session(
        session,
        employee_id=employee.id,
        token_hash=hash_token(session_token),
        expires_at=expires_at,
        last_seen_at=now,
    )
    return session_token, expires_at


def actor_from_authorization(
    session: Session,
    authorization: str | None,
    *,
    now: datetime,
) -> Employee | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthOperationError("Некорректный заголовок авторизации.", 401)
    auth_session = repository.find_auth_session_by_token_hash(session, hash_token(token))
    if auth_session is None or auth_session.revoked_at is not None:
        raise AuthOperationError("Сессия не найдена или завершена.", 401)
    if auth_session.expires_at < now:
        raise AuthOperationError("Срок действия сессии истек.", 401)
    if not auth_session.employee.is_active:
        raise AuthOperationError("Пользователь отключен.", 403)
    auth_session.last_seen_at = now
    return auth_session.employee


def logout_session(
    session: Session,
    authorization: str | None,
    *,
    now: datetime,
) -> dict[str, object]:
    if not authorization:
        return {"revoked": False}
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return {"revoked": False}
    auth_session = repository.find_auth_session_by_token_hash(session, hash_token(token))
    if auth_session is None or auth_session.revoked_at is not None:
        return {"revoked": False}
    auth_session.revoked_at = now
    repository.audit(
        session,
        auth_session.employee_id,
        "auth.session_revoked",
        "employee",
        auth_session.employee_id,
        {"is_demo": auth_session.employee.is_demo},
    )
    return {"revoked": True}
