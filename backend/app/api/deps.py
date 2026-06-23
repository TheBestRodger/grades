from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from typing import Any
from ..features.auth.errors import AuthOperationError
from ..features.auth.service import actor_from_authorization
from ..core.config import Settings
from ..core.db import Database
from ..models import Employee
from ..features.organization.service import require_actor


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_ai_gateway(request: Request) -> Any:
    return request.app.state.ai_gateway


def get_document_storage_dir(request: Request) -> Path:
    return request.app.state.document_storage_dir


def get_session(database: Database = Depends(get_database)) -> Iterator[Session]:
    with database.session() as session:
        yield session


def current_actor(
    authorization: str | None = Header(default=None),
    x_demo_user_id: int | None = Header(default=None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Employee:
    try:
        session_actor = actor_from_authorization(session, authorization)
    except AuthOperationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if session_actor is not None:
        return session_actor
    if settings.app_env not in {"demo-local", "test"}:
        raise HTTPException(status_code=401, detail="Войдите по одноразовой ссылке.")
    if x_demo_user_id is None:
        raise HTTPException(
            status_code=401, detail="Войдите или выберите пользователя."
        )
    actor = require_actor(session, x_demo_user_id)
    if actor is None:
        raise HTTPException(status_code=403, detail="Пользователь не найден.")
    return actor


def current_hr(actor: Employee = Depends(current_actor)) -> Employee:
    if actor.system_role != "hr" and not actor.is_hr:
        raise HTTPException(status_code=403, detail="HR access is required.")
    return actor


def actor_demo_scope(actor: Employee = Depends(current_actor)) -> bool:
    return actor.is_demo
