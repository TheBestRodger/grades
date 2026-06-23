from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import CampaignParticipant, Employee, EmployeeProfile
from .schemas import ProfileAnswersRequest
from .draft import save_draft
from .questionnaire import get_effective_profile_questions
from .repository import load_my_active_participants
from .serializers import serialize_profile
from .submit import submit_profile


def get_my_profiles(session: Session, actor: Employee) -> list[dict[str, object]]:
    participants = load_my_active_participants(session, actor)
    profiles = [ensure_profile(session, participant) for participant in participants]
    session.flush()
    questions = get_effective_profile_questions(session)
    return [serialize_profile(profile, questions) for profile in profiles]


def ensure_profile(session: Session, participant: CampaignParticipant) -> EmployeeProfile:
    if participant.profile is not None:
        return participant.profile
    profile = EmployeeProfile(campaign_participant_id=participant.id)
    session.add(profile)
    session.flush()
    participant.profile = profile
    return profile


_ensure_profile = ensure_profile
