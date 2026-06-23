from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Employee
from ..organization.service import unit_descendants
from . import repository
from .audit import audit
from .errors import CampaignOperationError
from .participants import (
    get_campaign_with_participants,
    resolve_editable_wave,
    set_participation,
    set_work_scope,
)
from .serializers import campaign_summary


def include_unit_in_campaign(
    session: Session,
    actor: Employee,
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = get_campaign_with_participants(session, campaign_id, is_demo)
    unit = _get_unit(session, org_unit_id, is_demo)
    wave = resolve_editable_wave(session, actor, campaign, wave_id)
    unit_ids = unit_descendants(repository.load_units(session, is_demo), {unit.id})

    if not is_demo:
        changed_units = set_work_scope(session, actor, wave, unit_ids, included=True)
        assignments = repository.load_assignments_for_units(session, unit_ids, is_demo=False)
        created = set_participation(session, actor, campaign, wave, assignments, included=True)
        session.flush()
        session.expire(campaign, ["participants", "waves"])
        audit(
            session,
            actor,
            "campaign.branch_included",
            "campaign",
            campaign.id,
            {
                "scope": "work",
                "org_unit_id": unit.id,
                "org_unit_name": unit.name,
                "wave_id": wave.id,
                "wave_name": wave.name,
                "selected_units_changed": changed_units,
                "new_participants": created,
            },
        )
        result = campaign_summary(session, campaign)
        result.update(
            {
                "included_unit_name": unit.name,
                "included_wave_id": wave.id,
                "included_wave_name": wave.name,
                "new_participants": created,
                "selected_units_changed": changed_units,
            }
        )
        return result

    assignments = repository.load_assignments_for_units(session, unit_ids, is_demo=True)
    created = set_participation(session, actor, campaign, wave, assignments, included=True)
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    audit(
        session,
        actor,
        "campaign.branch_included",
        "campaign",
        campaign.id,
        {
            "org_unit_id": unit.id,
            "org_unit_name": unit.name,
            "wave_id": wave.id,
            "wave_name": wave.name,
            "new_participants": created,
            "scope": "demo",
        },
    )
    result = campaign_summary(session, campaign)
    result.update(
        {
            "included_unit_name": unit.name,
            "included_wave_id": wave.id,
            "included_wave_name": wave.name,
            "new_participants": created,
        }
    )
    return result


def exclude_unit_from_campaign(
    session: Session,
    actor: Employee,
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = get_campaign_with_participants(session, campaign_id, is_demo)
    unit = _get_unit(session, org_unit_id, is_demo)
    wave = resolve_editable_wave(session, actor, campaign, wave_id)
    unit_ids = unit_descendants(repository.load_units(session, is_demo), {unit.id})

    if not is_demo:
        changed_units = set_work_scope(session, actor, wave, unit_ids, included=False)
        assignments = repository.load_assignments_for_units(session, unit_ids, is_demo=False)
        excluded = set_participation(session, actor, campaign, wave, assignments, included=False)
        result = _audit_excluded_unit(session, actor, campaign, wave, unit, excluded, "work", changed_units)
        result.update({"selected_units_changed": changed_units})
        return result

    assignment_ids = repository.load_assignment_ids_for_units(session, unit_ids, is_demo=True)
    excluded = 0
    for participant in campaign.participants:
        if participant.campaign_wave_id != wave.id:
            continue
        if participant.assignment_id not in assignment_ids:
            continue
        if not participant.expected_to_submit and participant.participation_status == "excluded":
            continue
        participant.expected_to_submit = False
        participant.participation_status = "excluded"
        excluded += 1
    return _audit_excluded_unit(session, actor, campaign, wave, unit, excluded, "demo", None)


def _audit_excluded_unit(session, actor, campaign, wave, unit, excluded, scope, changed_units):
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    details = {
        "org_unit_id": unit.id,
        "org_unit_name": unit.name,
        "wave_id": wave.id,
        "wave_name": wave.name,
        "excluded_participants": excluded,
        "scope": scope,
    }
    if changed_units is not None:
        details["selected_units_changed"] = changed_units
    audit(session, actor, "campaign.branch_excluded", "campaign", campaign.id, details)
    result = campaign_summary(session, campaign)
    result.update(
        {
            "excluded_unit_name": unit.name,
            "excluded_wave_id": wave.id,
            "excluded_wave_name": wave.name,
            "excluded_participants": excluded,
        }
    )
    return result


def _get_unit(session: Session, org_unit_id: int, is_demo: bool):
    unit = repository.load_unit(session, org_unit_id, is_demo)
    if unit is None:
        raise CampaignOperationError("Ветка структуры не найдена.", 404)
    return unit
