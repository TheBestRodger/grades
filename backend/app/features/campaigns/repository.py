from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import (
    Assignment,
    Campaign,
    CampaignParticipant,
    CampaignWave,
    Employee,
    EmployeeProfile,
    OrgUnit,
    StaffingLine,
)


def campaign_options():
    return (
        selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
        selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
    )


def load_campaigns(session: Session, is_demo: bool = True) -> list[Campaign]:
    return session.scalars(
        select(Campaign)
        .where(Campaign.is_demo.is_(is_demo))
        .options(*campaign_options())
        .order_by(Campaign.id.desc())
    ).all()


def load_campaign(session: Session, campaign_id: int, is_demo: bool = True) -> Campaign | None:
    return session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(*campaign_options())
    )


def load_campaign_with_participants(
    session: Session,
    campaign_id: int,
    is_demo: bool = True,
) -> Campaign | None:
    return session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.is_demo.is_(is_demo))
        .options(
            selectinload(Campaign.participants).selectinload(CampaignParticipant.profile),
            selectinload(Campaign.waves).selectinload(CampaignWave.unit_selections),
        )
    )


def load_wave(
    session: Session,
    campaign: Campaign,
    wave_id: int,
) -> CampaignWave | None:
    return session.scalar(
        select(CampaignWave).where(
            CampaignWave.id == wave_id,
            CampaignWave.campaign_id == campaign.id,
            CampaignWave.is_demo.is_(campaign.is_demo),
        )
    )


def load_unit(session: Session, org_unit_id: int, is_demo: bool = True) -> OrgUnit | None:
    return session.scalar(select(OrgUnit).where(OrgUnit.id == org_unit_id, OrgUnit.is_demo.is_(is_demo)))


def load_units(session: Session, is_demo: bool = True) -> list[OrgUnit]:
    return session.scalars(select(OrgUnit).where(OrgUnit.is_demo.is_(is_demo))).all()


def load_assignments_for_units(
    session: Session,
    unit_ids: set[int],
    is_demo: bool = True,
) -> list[Assignment]:
    return session.scalars(
        select(Assignment).where(
            Assignment.is_demo.is_(is_demo),
            Assignment.staffing_line_id.in_(
                select(StaffingLine.id).where(StaffingLine.org_unit_id.in_(unit_ids))
            ),
        )
    ).all()


def load_assignment_ids_for_units(
    session: Session,
    unit_ids: set[int],
    is_demo: bool = True,
) -> set[int]:
    return set(
        session.scalars(
            select(Assignment.id).where(
                Assignment.is_demo.is_(is_demo),
                Assignment.staffing_line_id.in_(
                    select(StaffingLine.id).where(StaffingLine.org_unit_id.in_(unit_ids))
                ),
            )
        ).all()
    )


def load_assignments_by_ids(
    session: Session,
    assignment_ids: list[int],
    is_demo: bool = True,
) -> list[Assignment]:
    return session.scalars(
        select(Assignment).where(
            Assignment.id.in_(assignment_ids),
            Assignment.is_demo.is_(is_demo),
        )
    ).all()


def load_new_wave_participants(
    session: Session,
    campaign: Campaign,
    wave: CampaignWave,
    is_demo: bool,
) -> list[CampaignParticipant]:
    return session.scalars(
        select(CampaignParticipant)
        .join(CampaignParticipant.assignment)
        .join(Assignment.employee)
        .join(Assignment.staffing_line)
        .where(
            CampaignParticipant.campaign_id == campaign.id,
            CampaignParticipant.campaign_wave_id == wave.id,
            CampaignParticipant.participation_status == "included",
            CampaignParticipant.expected_to_submit.is_(True),
            Assignment.is_demo.is_(is_demo),
            Employee.is_active.is_(True),
            Employee.first_login_at.is_(None),
        )
        .options(
            selectinload(CampaignParticipant.assignment).selectinload(Assignment.employee),
            selectinload(CampaignParticipant.assignment).selectinload(Assignment.staffing_line),
        )
        .order_by(Employee.full_name, StaffingLine.title)
    ).all()


def selected_unit_staffing_lines(session: Session, selected_unit_ids: list[int]) -> list[StaffingLine]:
    return session.scalars(
        select(StaffingLine).where(StaffingLine.org_unit_id.in_(selected_unit_ids))
    ).all()
