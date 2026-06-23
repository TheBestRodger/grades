from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee


def audit_work_employee_import(
    session: Session,
    actor: Employee,
    source_name: str,
    digest: str,
    rows_count: int,
    stats: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="employees.work_imported",
            entity_type="employee_import",
            entity_id=digest[:16],
            details_json=json.dumps(
                {
                    "scope": "work",
                    "filename": source_name,
                    "sha256": digest,
                    "rows": rows_count,
                    **stats,
                },
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
