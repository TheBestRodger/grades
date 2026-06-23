from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee
from .time import now


def audit_profile_event(
    session: Session,
    actor: Employee,
    action: str,
    entity_id: int,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type="employee_profile",
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
            created_at=now(),
        )
    )


_audit = audit_profile_event
