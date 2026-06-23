from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee


def audit(
    session: Session,
    actor: Employee,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
        )
    )


_audit = audit
