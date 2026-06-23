from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...api.deps import current_actor, get_session
from ...api.errors import run_operation
from ...models import Employee
from .service import (
    get_notifications,
    get_unread_count,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter()


@router.get("/api/notifications")
def notifications(
    limit: int = Query(default=50, ge=1, le=100),
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_notifications(session, actor, limit)


@router.get("/api/notifications/unread-count")
def notification_unread_count(
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    return get_unread_count(session, actor)


@router.post("/api/notifications/read-all")
def read_all_notifications(
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    return mark_all_notifications_read(session, actor)


@router.post("/api/notifications/{notification_id}/read")
def read_notification(
    notification_id: int,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: mark_notification_read(session, actor, notification_id))
