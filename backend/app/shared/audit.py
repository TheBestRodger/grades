from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import AuditEvent


def add_audit_event(
    session: Session,
    *,
    actor_employee_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor_employee_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
        )
    )
