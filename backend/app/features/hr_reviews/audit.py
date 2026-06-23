from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee, EmployeeProfile, ProfileReviewEvent, ProfileRevision


def record_review_action(
    session: Session,
    actor: Employee,
    profile: EmployeeProfile,
    revision: ProfileRevision,
    action: str,
    audit_action: str,
    comment: str | None,
) -> None:
    profile.review_events.append(
        ProfileReviewEvent(
            revision=revision,
            actor=actor,
            action=action,
            comment=comment,
        )
    )
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=audit_action,
            entity_type="employee_profile",
            entity_id=str(profile.id),
            details_json=json.dumps(
                {"revision_no": revision.revision_no, "comment": comment},
                ensure_ascii=False,
            ),
        )
    )


_record = record_review_action
