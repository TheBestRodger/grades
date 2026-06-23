from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...models import (
    Assignment,
    Campaign,
    CampaignParticipant,
    Employee,
    EmployeeProfile,
    ProfileReviewEvent,
    StaffingLine,
)
from .errors import ReviewOperationError


def manager_assignment_ids(session: Session, actor: Employee) -> list[int]:
    if actor.system_role != "manager":
        raise ReviewOperationError("Действие доступно только руководителю.", 403)
    return list(
        session.scalars(
            select(Assignment.id).where(
                Assignment.employee_id == actor.id,
            )
        ).all()
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


def direct_profile_query(session: Session, actor: Employee):
    assignment_ids = manager_assignment_ids(session, actor)
    if not assignment_ids:
        return select(EmployeeProfile).where(EmployeeProfile.id == -1)
    return (
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.assignment)
        .join(CampaignParticipant.campaign)
        .where(
            Assignment.manager_assignment_id.in_(assignment_ids),
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
            Campaign.status == "active",
        )
        .options(*profile_options())
    )


def load_review_queue(session: Session, actor: Employee) -> list[EmployeeProfile]:
    return session.scalars(direct_profile_query(session, actor).order_by(EmployeeProfile.id)).all()


def load_direct_profile(
    session: Session,
    actor: Employee,
    profile_id: int,
) -> EmployeeProfile | None:
    return session.scalar(direct_profile_query(session, actor).where(EmployeeProfile.id == profile_id))
