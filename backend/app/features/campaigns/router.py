from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...api.deps import current_hr, get_session
from ...api.errors import run_operation
from ...models import Employee
from .schemas import CampaignAssignmentsUpdate, CampaignCreate, CampaignWaveCreate
from .service import (
    create_campaign,
    create_campaign_wave,
    edit_campaign_wave,
    exclude_unit_from_campaign,
    get_campaigns,
    include_unit_in_campaign,
    launch_campaign_wave,
    set_campaign_assignments,
)

router = APIRouter()


@router.get("/api/hr/campaigns")
def campaigns(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return get_campaigns(session)


@router.post("/api/hr/campaigns")
def add_campaign(
    request: CampaignCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: create_campaign(session, actor, request))


@router.post("/api/hr/campaigns/{campaign_id}/waves")
def add_campaign_wave(
    campaign_id: int,
    request: CampaignWaveCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: create_campaign_wave(session, actor, campaign_id, request))


@router.post("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/launch")
def launch_demo_campaign_wave(
    campaign_id: int,
    wave_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: launch_campaign_wave(session, actor, campaign_id, wave_id))


@router.post("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/edit")
def edit_demo_campaign_wave(
    campaign_id: int,
    wave_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: edit_campaign_wave(session, actor, campaign_id, wave_id))


@router.post("/api/hr/campaigns/{campaign_id}/include-unit/{org_unit_id}")
def include_branch(
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: include_unit_in_campaign(session, actor, campaign_id, org_unit_id, wave_id)
    )


@router.post("/api/hr/campaigns/{campaign_id}/exclude-unit/{org_unit_id}")
def exclude_branch(
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: exclude_unit_from_campaign(session, actor, campaign_id, org_unit_id, wave_id)
    )


@router.put("/api/hr/campaigns/{campaign_id}/waves/{wave_id}/assignments")
def update_demo_campaign_assignments(
    campaign_id: int,
    wave_id: int,
    request: CampaignAssignmentsUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: set_campaign_assignments(session, actor, campaign_id, wave_id, request))


@router.get("/api/work/hr/campaigns")
def work_campaigns(
    _: Employee = Depends(current_hr), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return get_campaigns(session, is_demo=False)


@router.post("/api/work/hr/campaigns")
def add_work_campaign(
    request: CampaignCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: create_campaign(session, actor, request, is_demo=False))


@router.post("/api/work/hr/campaigns/{campaign_id}/waves")
def add_work_campaign_wave(
    campaign_id: int,
    request: CampaignWaveCreate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: create_campaign_wave(session, actor, campaign_id, request, is_demo=False)
    )


@router.post("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/launch")
def launch_work_campaign_wave(
    campaign_id: int,
    wave_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: launch_campaign_wave(session, actor, campaign_id, wave_id, is_demo=False))


@router.post("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/edit")
def edit_work_campaign_wave(
    campaign_id: int,
    wave_id: int,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: edit_campaign_wave(session, actor, campaign_id, wave_id, is_demo=False))


@router.post("/api/work/hr/campaigns/{campaign_id}/include-unit/{org_unit_id}")
def include_work_branch(
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: include_unit_in_campaign(
            session, actor, campaign_id, org_unit_id, wave_id, is_demo=False
        )
    )


@router.post("/api/work/hr/campaigns/{campaign_id}/exclude-unit/{org_unit_id}")
def exclude_work_branch(
    campaign_id: int,
    org_unit_id: int,
    wave_id: int | None = None,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: exclude_unit_from_campaign(
            session, actor, campaign_id, org_unit_id, wave_id, is_demo=False
        )
    )


@router.put("/api/work/hr/campaigns/{campaign_id}/waves/{wave_id}/assignments")
def update_work_campaign_assignments(
    campaign_id: int,
    wave_id: int,
    request: CampaignAssignmentsUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(
        lambda: set_campaign_assignments(session, actor, campaign_id, wave_id, request, is_demo=False)
    )
