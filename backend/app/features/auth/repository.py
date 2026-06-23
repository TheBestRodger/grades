from __future__ import annotations

from datetime import datetime
import json

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ...models import AuditEvent, AuthLoginToken, AuthSession, Employee


def audit(
    session: Session,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
        )
    )


def find_bootstrap_hr(session: Session) -> Employee | None:
    return session.scalar(
        select(Employee)
        .where(
            (Employee.system_role == "hr") | (Employee.is_hr.is_(True)),
            Employee.is_active.is_(True),
        )
        .order_by(Employee.id)
    )


def find_active_employee_by_login(session: Session, normalized_login: str) -> Employee | None:
    return session.scalar(
        select(Employee).where(
            or_(
                func.lower(Employee.username) == normalized_login,
                func.lower(Employee.email) == normalized_login,
            ),
            Employee.is_active.is_(True),
        )
    )


def find_active_employee_by_email(session: Session, normalized_email: str) -> Employee | None:
    return session.scalar(
        select(Employee).where(
            func.lower(Employee.email) == normalized_email,
            Employee.is_active.is_(True),
        )
    )


def add_login_token(
    session: Session,
    *,
    employee_id: int,
    token_hash: str,
    expires_at: datetime,
) -> AuthLoginToken:
    login_token = AuthLoginToken(
        employee_id=employee_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(login_token)
    return login_token


def find_login_token_by_hash(session: Session, token_hash: str) -> AuthLoginToken | None:
    return session.scalar(
        select(AuthLoginToken)
        .where(AuthLoginToken.token_hash == token_hash)
        .options(selectinload(AuthLoginToken.employee))
    )


def add_auth_session(
    session: Session,
    *,
    employee_id: int,
    token_hash: str,
    expires_at: datetime,
    last_seen_at: datetime,
) -> AuthSession:
    auth_session = AuthSession(
        employee_id=employee_id,
        token_hash=token_hash,
        expires_at=expires_at,
        last_seen_at=last_seen_at,
    )
    session.add(auth_session)
    return auth_session


def find_auth_session_by_token_hash(session: Session, token_hash: str) -> AuthSession | None:
    return session.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == token_hash)
        .options(selectinload(AuthSession.employee))
    )
