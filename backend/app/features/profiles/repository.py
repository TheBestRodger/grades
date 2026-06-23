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
    QuestionnaireQuestionSetting,
    StaffingLine,
)


def load_question_settings(session: Session) -> list[QuestionnaireQuestionSetting]:
    return session.scalars(select(QuestionnaireQuestionSetting)).all()


def load_my_active_participants(session: Session, actor: Employee) -> list[CampaignParticipant]:
    return session.scalars(
        select(CampaignParticipant)
        .join(CampaignParticipant.assignment)
        .join(CampaignParticipant.campaign)
        .where(
            Assignment.employee_id == actor.id,
            CampaignParticipant.expected_to_submit.is_(True),
            CampaignParticipant.participation_status == "included",
            Campaign.status == "active",
        )
        .options(
            selectinload(CampaignParticipant.campaign),
            selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(CampaignParticipant.profile).selectinload(EmployeeProfile.draft),
            selectinload(CampaignParticipant.profile).selectinload(EmployeeProfile.revisions),
            selectinload(CampaignParticipant.profile)
            .selectinload(EmployeeProfile.review_events)
            .selectinload(ProfileReviewEvent.revision),
            selectinload(CampaignParticipant.profile)
            .selectinload(EmployeeProfile.review_events)
            .selectinload(ProfileReviewEvent.actor),
        )
        .order_by(CampaignParticipant.id.desc())
    ).all()


def load_owned_profile(
    session: Session,
    actor: Employee,
    profile_id: int,
) -> EmployeeProfile | None:
    return session.scalar(
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.assignment)
        .where(EmployeeProfile.id == profile_id, Assignment.employee_id == actor.id)
        .options(
            selectinload(EmployeeProfile.participant).selectinload(CampaignParticipant.campaign),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.manager)
            .selectinload(Assignment.employee),
            selectinload(EmployeeProfile.draft),
            selectinload(EmployeeProfile.revisions),
            selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.revision),
            selectinload(EmployeeProfile.review_events).selectinload(ProfileReviewEvent.actor),
        )
    )
