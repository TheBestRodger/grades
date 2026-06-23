from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Campaign, CampaignParticipant, CampaignWave, StaffingLine
from . import repository
from .rules import can_launch_wave, is_wave_editable, wave_status_label


def participants_for_wave(
    campaign: Campaign,
    wave: CampaignWave | None,
) -> list[CampaignParticipant]:
    return [
        participant
        for participant in campaign.participants
        if participant.campaign_wave_id == (wave.id if wave else None)
    ]


def included_participants(participants: list[CampaignParticipant]) -> list[CampaignParticipant]:
    return [participant for participant in participants if participant.expected_to_submit]


def status_counts(participants: list[CampaignParticipant]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for participant in included_participants(participants):
        status = participant.profile.workflow_status if participant.profile else "not_started"
        counts[status] = counts.get(status, 0) + 1
    return counts


def selected_unit_ids(wave: CampaignWave) -> list[int]:
    return sorted(
        selection.org_unit_id
        for selection in wave.unit_selections
        if selection.inclusion_status == "included"
    )


def wave_scope_metrics(session: Session, wave: CampaignWave) -> dict[str, object]:
    unit_ids = selected_unit_ids(wave)
    if not unit_ids:
        return {
            "selected_org_unit_ids": [],
            "selected_units_count": 0,
            "selected_staffing_lines": 0,
            "selected_approved_fte": 0.0,
        }
    lines = repository.selected_unit_staffing_lines(session, unit_ids)
    return {
        "selected_org_unit_ids": unit_ids,
        "selected_units_count": len(unit_ids),
        "selected_staffing_lines": len(lines),
        "selected_approved_fte": round(sum(line.approved_fte for line in lines), 2),
    }


def wave_summary(session: Session, campaign: Campaign, wave: CampaignWave) -> dict[str, object]:
    participants = participants_for_wave(campaign, wave)
    included = included_participants(participants)
    return {
        "id": wave.id,
        "campaign_id": campaign.id,
        "name": wave.name,
        "status": wave.status,
        "status_label": wave_status_label(wave.status),
        "can_edit": is_wave_editable(wave.status),
        "can_launch": can_launch_wave(wave.status, len(included)),
        "due_at": wave.due_at.isoformat() if wave.due_at else None,
        "participants_expected": len(included),
        "participant_assignment_ids": [participant.assignment_id for participant in included],
        "status_counts": status_counts(participants),
        "created_at": wave.created_at.isoformat() if wave.created_at else None,
        **wave_scope_metrics(session, wave),
    }


def campaign_summary(session: Session, campaign: Campaign) -> dict[str, object]:
    waves = [wave_summary(session, campaign, wave) for wave in campaign.waves]
    active_wave = next((wave for wave in reversed(waves) if wave["status"] == "active"), None)
    if active_wave is None and waves:
        active_wave = waves[-1]
    all_included = included_participants(list(campaign.participants))
    return {
        "id": campaign.id,
        "scope": "demo" if campaign.is_demo else "work",
        "is_demo": campaign.is_demo,
        "name": campaign.name,
        "status": campaign.status,
        "due_at": campaign.due_at.isoformat() if campaign.due_at else None,
        "participants_expected": active_wave["participants_expected"] if active_wave else 0,
        "participant_assignment_ids": active_wave["participant_assignment_ids"] if active_wave else [],
        "status_counts": active_wave["status_counts"] if active_wave else {},
        "selected_org_unit_ids": active_wave["selected_org_unit_ids"] if active_wave else [],
        "selected_units_count": active_wave["selected_units_count"] if active_wave else 0,
        "selected_staffing_lines": active_wave["selected_staffing_lines"] if active_wave else 0,
        "selected_approved_fte": active_wave["selected_approved_fte"] if active_wave else 0.0,
        "total_participants_expected": len(all_included),
        "active_wave_id": active_wave["id"] if active_wave else None,
        "active_wave_name": active_wave["name"] if active_wave else None,
        "waves": waves,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
    }


_participants_for_wave = participants_for_wave
_included_participants = included_participants
_status_counts = status_counts
_selected_unit_ids = selected_unit_ids
_wave_scope_metrics = wave_scope_metrics
_wave_summary = wave_summary
