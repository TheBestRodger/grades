"""Public service facade for campaigns feature use cases."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import AuditEvent
from .credentials import credentials_to_xlsx, issue_credentials_for_new_wave_participants  # noqa: F401
from .errors import CampaignOperationError  # noqa: F401
from .campaigns import create_campaign, get_campaigns  # noqa: F401
from .participants import (  # noqa: F401
    _set_participation,
    _set_work_scope,
    set_campaign_assignments,
    set_participation,
    set_work_scope,
)
from .units import exclude_unit_from_campaign, include_unit_in_campaign  # noqa: F401
from .serializers import (  # noqa: F401
    _included_participants,
    _participants_for_wave,
    _selected_unit_ids,
    _status_counts,
    _wave_scope_metrics,
    _wave_summary,
    campaign_summary,
    included_participants,
    participants_for_wave,
    selected_unit_ids,
    status_counts,
    wave_scope_metrics,
    wave_summary,
)
from .waves import (  # noqa: F401
    _default_wave,
    _resolve_wave,
    create_campaign_wave,
    default_wave,
    edit_campaign_wave,
    launch_campaign_wave,
    resolve_wave,
)


def recent_audit_events(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    events = session.scalars(
        select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100)
    ).all()
    results: list[dict[str, object]] = []
    for event in events:
        details = json.loads(event.details_json) if event.details_json else {}
        scope = details.get("scope", "demo")
        if scope != ("demo" if is_demo else "work"):
            continue
        results.append(
            {
                "id": event.id,
                "action": event.action,
                "entity_type": event.entity_type,
                "details": details,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
        )
        if len(results) == 12:
            break
    return results
