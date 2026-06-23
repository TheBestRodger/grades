from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import (
    Assignment,
    Campaign,
    CampaignParticipant,
    CampaignWave,
    CampaignWaveUnitSelection,
    Employee,
    EmployeeProfile,
)
from . import repository
from .audit import audit
from .errors import CampaignOperationError
from .rules import is_wave_editable
from .schemas import CampaignAssignmentsUpdate
from .serializers import campaign_summary
from .waves import resolve_wave
from ..notifications.service import create_notification


def set_campaign_assignments(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    request: CampaignAssignmentsUpdate,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = get_campaign_with_participants(session, campaign_id, is_demo)
    wave = resolve_editable_wave(session, actor, campaign, wave_id)
    assignments = repository.load_assignments_by_ids(session, request.assignment_ids, is_demo)
    if {assignment.id for assignment in assignments} != set(request.assignment_ids):
        raise CampaignOperationError("Одно или несколько назначений не найдены в выбранном контуре.", 404)
    included = request.action == "include"
    changed = set_participation(session, actor, campaign, wave, assignments, included)
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    action = "campaign.assignments_included" if included else "campaign.assignments_excluded"
    audit(
        session,
        actor,
        action,
        "campaign",
        campaign.id,
        {
            "scope": "demo" if is_demo else "work",
            "wave_id": wave.id,
            "wave_name": wave.name,
            "assignment_ids": request.assignment_ids,
            "changed_participants": changed,
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"changed_participants": changed, "participant_action": request.action})
    return result


def set_work_scope(
    session: Session,
    actor: Employee,
    wave: CampaignWave,
    unit_ids: set[int],
    included: bool,
) -> int:
    existing = {selection.org_unit_id: selection for selection in wave.unit_selections}
    next_status = "included" if included else "excluded"
    changed = 0
    for unit_id in unit_ids:
        selection = existing.get(unit_id)
        if selection is None:
            selection = CampaignWaveUnitSelection(
                wave=wave,
                org_unit_id=unit_id,
                inclusion_status=next_status,
                selected_by_id=actor.id,
                is_demo=False,
            )
            session.add(selection)
            changed += 1
            continue
        if selection.inclusion_status != next_status:
            selection.inclusion_status = next_status
            selection.selected_by_id = actor.id
            changed += 1
    return changed


def set_participation(
    session: Session,
    actor: Employee,
    campaign: Campaign,
    wave: CampaignWave,
    assignments: list[Assignment],
    included: bool,
) -> int:
    existing = {participant.assignment_id: participant for participant in campaign.participants}
    changed = 0
    for assignment in assignments:
        participant = existing.get(assignment.id)
        if participant is None:
            if not included:
                continue
            participant = CampaignParticipant(
                campaign=campaign,
                wave=wave,
                assignment_id=assignment.id,
                participation_status="included",
                expected_to_submit=True,
                included_by_id=actor.id,
            )
            participant.profile = EmployeeProfile()
            session.add(participant)
            create_notification(
                session,
                recipient_id=assignment.employee_id,
                notification_type="profile_assigned",
                title="Назначена новая анкета",
                message=f"Вы включены в кампанию «{campaign.name}», волна «{wave.name}».",
                target_section="profile",
                entity_type="campaign",
                entity_id=campaign.id,
                dedupe_key=f"profile-assigned:{campaign.id}:{assignment.id}",
            )
            changed += 1
            continue
        if participant.campaign_wave_id != wave.id:
            continue
        next_status = "included" if included else "excluded"
        if (
            participant.expected_to_submit == included
            and participant.participation_status == next_status
        ):
            continue
        participant.expected_to_submit = included
        participant.participation_status = next_status
        changed += 1
    return changed


def get_campaign_with_participants(
    session: Session,
    campaign_id: int,
    is_demo: bool,
) -> Campaign:
    campaign = repository.load_campaign_with_participants(session, campaign_id, is_demo)
    if campaign is None:
        raise CampaignOperationError("Кампания не найдена.", 404)
    return campaign


def resolve_editable_wave(
    session: Session,
    actor: Employee,
    campaign: Campaign,
    wave_id: int | None,
) -> CampaignWave:
    wave = resolve_wave(session, actor, campaign, wave_id)
    if not is_wave_editable(wave.status):
        raise CampaignOperationError(
            "Волна запущена. Чтобы изменить участников, сначала возьмите волну в редакцию.",
            409,
        )
    return wave


_set_work_scope = set_work_scope
_set_participation = set_participation
