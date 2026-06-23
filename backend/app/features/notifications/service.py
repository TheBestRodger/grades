from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from ...models import Employee, Notification
from . import repository
from .errors import NotificationOperationError


def create_notification(
    session: Session,
    *,
    recipient_id: int,
    notification_type: str,
    title: str,
    message: str,
    target_section: str | None = None,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    dedupe_key: str | None = None,
) -> Notification:
    recipient_dedupe_key = f"{dedupe_key}:{recipient_id}" if dedupe_key else None
    if recipient_dedupe_key:
        pending = next(
            (
                item
                for item in session.new
                if isinstance(item, Notification)
                and item.dedupe_key == recipient_dedupe_key
            ),
            None,
        )
        if pending is not None:
            return pending

        existing = repository.load_by_dedupe_key(session, recipient_dedupe_key)
        if existing is not None:
            return existing

    notification = Notification(
        recipient_employee_id=recipient_id,
        notification_type=notification_type,
        title=title,
        message=message,
        target_section=target_section,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        dedupe_key=recipient_dedupe_key,
    )
    session.add(notification)
    return notification


def notify_hr_users(
    session: Session,
    *,
    is_demo: bool,
    notification_type: str,
    title: str,
    message: str,
    target_section: str,
    entity_type: str,
    entity_id: int | str,
    dedupe_key: str,
    exclude_employee_id: int | None = None,
) -> list[Notification]:
    return [
        create_notification(
            session,
            recipient_id=recipient.id,
            notification_type=notification_type,
            title=title,
            message=message,
            target_section=target_section,
            entity_type=entity_type,
            entity_id=entity_id,
            dedupe_key=dedupe_key,
        )
        for recipient in repository.load_hr_recipients(
            session,
            is_demo=is_demo,
            exclude_employee_id=exclude_employee_id,
        )
    ]


def get_notifications(
    session: Session,
    actor: Employee,
    limit: int = 50,
) -> dict[str, object]:
    notifications = repository.load_notifications(session, actor.id, limit)
    return {
        "items": [serialize_notification(notification) for notification in notifications],
        "unread_count": repository.unread_count(session, actor.id),
    }


def get_unread_count(session: Session, actor: Employee) -> dict[str, int]:
    return {"unread_count": repository.unread_count(session, actor.id)}


def mark_notification_read(
    session: Session,
    actor: Employee,
    notification_id: int,
) -> dict[str, object]:
    notification = repository.load_recipient_notification(session, actor.id, notification_id)
    if notification is None:
        raise NotificationOperationError("Уведомление не найдено.", 404)
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC).replace(tzinfo=None)
        session.flush()
    return serialize_notification(notification)


def mark_all_notifications_read(session: Session, actor: Employee) -> dict[str, int]:
    result = session.execute(
        update(Notification)
        .where(
            Notification.recipient_employee_id == actor.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC).replace(tzinfo=None))
    )
    return {"updated": int(result.rowcount or 0)}


def serialize_notification(notification: Notification) -> dict[str, object]:
    return {
        "id": notification.id,
        "notification_type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "entity_type": notification.entity_type,
        "entity_id": notification.entity_id,
        "target_section": notification.target_section,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }
