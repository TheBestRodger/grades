from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee, EmployeeProfile, ProfileReviewEvent, ProfileRevision


def audit_review_action(
    session: Session,
    actor: Employee,
    action: str,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type="employee_profile",
            entity_id=str(profile.id),
            details_json=json.dumps(
                {"revision_no": revision.revision_no, **details},
                ensure_ascii=False,
            ),
        )
    )


def add_review_event(
    profile: EmployeeProfile,
    revision: ProfileRevision,
    actor: Employee,
    action: str,
    comment: str | None = None,
) -> None:
    profile.review_events.append(
        ProfileReviewEvent(
            revision=revision,
            actor=actor,
            action=action,
            comment=comment,
        )
    )


_audit = audit_review_action
_add_review_event = add_review_event
