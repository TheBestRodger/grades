from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import secrets

from sqlalchemy.orm import Session

from ...models import AuthLoginToken, Employee
from .errors import AuthOperationError
from . import repository

MAGIC_LINK_TTL_MINUTES = 15


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def magic_link_expires_at(now: datetime) -> datetime:
    return now + timedelta(minutes=MAGIC_LINK_TTL_MINUTES)


def issue_magic_link_token(
    session: Session,
    employee: Employee,
    *,
    expires_at: datetime,
) -> str:
    token = new_token()
    repository.add_login_token(
        session,
        employee_id=employee.id,
        token_hash=hash_token(token),
        expires_at=expires_at,
    )
    return token


def load_valid_magic_link(
    session: Session,
    token: str,
    *,
    now: datetime,
) -> AuthLoginToken:
    login_token = repository.find_login_token_by_hash(session, hash_token(token))
    if login_token is None:
        raise AuthOperationError("Ссылка входа не найдена.", 401)
    if login_token.consumed_at is not None:
        raise AuthOperationError("Ссылка входа уже использована.", 409)
    if login_token.expires_at < now:
        raise AuthOperationError("Срок действия ссылки входа истек.", 401)
    if not login_token.employee.is_active:
        raise AuthOperationError("Пользователь отключен.", 403)
    return login_token
