from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Campaign, CampaignWave, Employee
from . import repository
from .audit import audit
from .errors import CampaignOperationError
from .rules import WAVE_STATUS_ACTIVE, WAVE_STATUS_DRAFT, WAVE_STATUS_EDITING, is_wave_editable
from .schemas import CampaignWaveCreate
from .serializers import campaign_summary, included_participants, participants_for_wave, selected_unit_ids


def create_campaign_wave(
    session: Session,
    actor: Employee,
    campaign_id: int,
    request: CampaignWaveCreate,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = get_campaign(session, campaign_id, is_demo)
    wave = CampaignWave(
        campaign=campaign,
        name=request.name,
        status=WAVE_STATUS_DRAFT,
        due_at=request.due_at,
        created_by_id=actor.id,
        is_demo=is_demo,
    )
    session.add(wave)
    session.flush()
    audit(
        session,
        actor,
        "campaign.wave_created",
        "campaign_wave",
        wave.id,
        {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "wave_name": wave.name,
            "due_at": request.due_at.isoformat() if request.due_at else None,
            "scope": "demo" if is_demo else "work",
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"new_wave_id": wave.id, "new_wave_name": wave.name})
    return result


def launch_campaign_wave(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = get_campaign(session, campaign_id, is_demo)
    wave = resolve_wave(session, actor, campaign, wave_id)
    if not is_wave_editable(wave.status):
        raise CampaignOperationError("Волна уже запущена.", 409)

    participants = included_participants(participants_for_wave(campaign, wave))
    if not participants:
        raise CampaignOperationError("Для запуска волны выберите минимум одного участника.", 422)
    unit_ids = selected_unit_ids(wave)

    previous_status = wave.status
    wave.status = WAVE_STATUS_ACTIVE
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    audit(
        session,
        actor,
        "campaign.wave_launched",
        "campaign_wave",
        wave.id,
        {
            "scope": "demo" if is_demo else "work",
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "wave_id": wave.id,
            "wave_name": wave.name,
            "previous_status": previous_status,
            "participants_expected": len(participants),
            "selected_units_count": len(unit_ids),
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"launched_wave_id": wave.id, "launched_wave_name": wave.name})
    return result


def edit_campaign_wave(
    session: Session,
    actor: Employee,
    campaign_id: int,
    wave_id: int,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = get_campaign(session, campaign_id, is_demo)
    wave = resolve_wave(session, actor, campaign, wave_id)
    if wave.status == WAVE_STATUS_DRAFT:
        raise CampaignOperationError("Волна уже находится в черновике и доступна для редактирования.", 409)
    if wave.status == WAVE_STATUS_EDITING:
        raise CampaignOperationError("Волна уже находится в редакции.", 409)
    if wave.status != WAVE_STATUS_ACTIVE:
        raise CampaignOperationError("Волну в текущем статусе нельзя взять в редакцию.", 409)

    wave.status = WAVE_STATUS_EDITING
    session.flush()
    session.expire(campaign, ["participants", "waves"])
    audit(
        session,
        actor,
        "campaign.wave_editing_started",
        "campaign_wave",
        wave.id,
        {
            "scope": "demo" if is_demo else "work",
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "wave_id": wave.id,
            "wave_name": wave.name,
        },
    )
    result = campaign_summary(session, campaign)
    result.update({"editing_wave_id": wave.id, "editing_wave_name": wave.name})
    return result


def resolve_wave(session: Session, actor: Employee, campaign: Campaign, wave_id: int | None) -> CampaignWave:
    if wave_id is None:
        return default_wave(session, actor, campaign)
    wave = repository.load_wave(session, campaign, wave_id)
    if wave is None:
        raise CampaignOperationError("Волна кампании не найдена.", 404)
    return wave


def default_wave(session: Session, actor: Employee, campaign: Campaign) -> CampaignWave:
    active_waves = [wave for wave in campaign.waves if wave.status == WAVE_STATUS_ACTIVE]
    if active_waves:
        return active_waves[-1]
    if campaign.waves:
        return campaign.waves[-1]
    wave = CampaignWave(
        campaign=campaign,
        name="Волна 1",
        status=WAVE_STATUS_DRAFT,
        due_at=campaign.due_at,
        created_by_id=actor.id,
        is_demo=campaign.is_demo,
    )
    session.add(wave)
    session.flush()
    session.expire(campaign, ["waves", "participants"])
    return wave


def get_campaign(session: Session, campaign_id: int, is_demo: bool) -> Campaign:
    campaign = repository.load_campaign(session, campaign_id, is_demo)
    if campaign is None:
        raise CampaignOperationError("Кампания не найдена.", 404)
    return campaign


_default_wave = default_wave
_resolve_wave = resolve_wave
