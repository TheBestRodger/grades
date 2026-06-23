from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import Campaign, CampaignWave, Employee
from . import repository
from .audit import audit
from .rules import WAVE_STATUS_DRAFT
from .schemas import CampaignCreate
from .serializers import campaign_summary


def get_campaigns(session: Session, is_demo: bool = True) -> list[dict[str, object]]:
    return [campaign_summary(session, campaign) for campaign in repository.load_campaigns(session, is_demo)]


def create_campaign(
    session: Session,
    actor: Employee,
    request: CampaignCreate,
    is_demo: bool = True,
) -> dict[str, object]:
    campaign = Campaign(
        name=request.name,
        status="active",
        due_at=request.due_at,
        created_by_id=actor.id,
        is_demo=is_demo,
    )
    session.add(campaign)
    session.flush()
    wave = CampaignWave(
        campaign=campaign,
        name="Волна 1",
        status=WAVE_STATUS_DRAFT,
        due_at=request.due_at,
        created_by_id=actor.id,
        is_demo=is_demo,
    )
    session.add(wave)
    session.flush()
    session.expire(campaign, ["waves", "participants"])
    audit(
        session,
        actor,
        "campaign.created",
        "campaign",
        campaign.id,
        {
            "name": campaign.name,
            "due_at": request.due_at.isoformat() if request.due_at else None,
            "initial_wave_id": wave.id,
            "initial_wave_name": wave.name,
            "scope": "demo" if is_demo else "work",
        },
    )
    return campaign_summary(session, campaign)
