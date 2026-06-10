from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from ...auth_operations import (
    consume_magic_link,
    employee_payload,
    login_with_password,
    logout_session,
    request_magic_link,
)
from ...config import Settings
from ...models import Employee
from ...schemas import MagicLinkConsumeRequest, MagicLinkRequest, PasswordLoginRequest
from ..deps import current_actor, get_session, get_settings
from ..errors import run_operation

router = APIRouter()


@router.post("/api/auth/magic-link/request")
def auth_magic_link_request(
    payload: MagicLinkRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return run_operation(lambda: request_magic_link(session, payload.email, settings))


@router.post("/api/auth/magic-link/consume")
def auth_magic_link_consume(
    payload: MagicLinkConsumeRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: consume_magic_link(session, payload.token))


@router.post("/api/auth/login")
def auth_password_login(
    payload: PasswordLoginRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: login_with_password(session, payload.username, payload.password)
    )


@router.post("/api/auth/logout")
def auth_logout(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return logout_session(session, authorization)


@router.get("/api/me")
def me(actor: Employee = Depends(current_actor)) -> dict[str, object]:
    return employee_payload(actor)
