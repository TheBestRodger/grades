from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import (
    Assignment,
    Campaign,
    CampaignParticipant,
    EmployeeProfile,
    ProfileReviewEvent,
    StaffingLine,
)


def profile_options():
    return (
        selectinload(EmployeeProfile.participant).selectinload(CampaignParticipant.campaign),
        selectinload(EmployeeProfile.participant)
        .selectinload(CampaignParticipant.assignment)
        .selectinload(Assignment.employee),
        selectinload(EmployeeProfile.participant)
        .selectinload(CampaignParticipant.assignment)
        .selectinload(Assignment.staffing_line)
        .selectinload(StaffingLine.org_unit),
        selectinload(EmployeeProfile.participant)
        .selectinload(CampaignParticipant.assignment)
        .selectinload(Assignment.manager)
        .selectinload(Assignment.employee),
        selectinload(EmployeeProfile.revisions),
        selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.revision),
        selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.actor),
    )


def profile_query(is_demo: bool = True):
    return (
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.campaign)
        .where(
            Campaign.is_demo.is_(is_demo),
            Campaign.status == "active",
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
        )
        .options(*profile_options())
    )


def load_hr_review_queue(session: Session, is_demo: bool = True) -> list[EmployeeProfile]:
    return session.scalars(profile_query(is_demo).order_by(EmployeeProfile.id)).all()


def load_profile(
    session: Session,
    profile_id: int,
    is_demo: bool = True,
) -> EmployeeProfile | None:
    return session.scalar(profile_query(is_demo).where(EmployeeProfile.id == profile_id))
