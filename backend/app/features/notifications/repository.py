from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ...models import Employee, Notification


def load_notifications(
    session: Session,
    recipient_id: int,
    limit: int,
) -> list[Notification]:
    return session.scalars(
        select(Notification)
        .where(Notification.recipient_employee_id == recipient_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    ).all()


def unread_count(session: Session, recipient_id: int) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_employee_id == recipient_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )


def load_recipient_notification(
    session: Session,
    recipient_id: int,
    notification_id: int,
) -> Notification | None:
    return session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_employee_id == recipient_id,
        )
    )


def load_by_dedupe_key(session: Session, dedupe_key: str) -> Notification | None:
    return session.scalar(select(Notification).where(Notification.dedupe_key == dedupe_key))


def load_hr_recipients(
    session: Session,
    *,
    is_demo: bool,
    exclude_employee_id: int | None = None,
) -> list[Employee]:
    conditions = [
        Employee.is_active.is_(True),
        or_(
            Employee.system_role == "hr",
            and_(
                Employee.is_hr.is_(True),
                Employee.is_demo.is_(is_demo),
            ),
        ),
    ]
    if exclude_employee_id is not None:
        conditions.append(Employee.id != exclude_employee_id)
    return session.scalars(select(Employee).where(*conditions).order_by(Employee.id)).all()
