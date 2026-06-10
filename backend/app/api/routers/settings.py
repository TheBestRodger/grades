from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...config import Settings
from ...models import Employee
from ...profile_operations import (
    get_questionnaire_settings,
    update_questionnaire_settings,
)
from ...schemas import AiConfigurationUpdate, QuestionnaireSettingsUpdate
from ...settings_operations import get_ai_configuration, update_ai_configuration
from ..deps import current_hr, get_session, get_settings
from ..errors import run_operation

router = APIRouter()


@router.get("/api/hr/settings/ai")
def hr_ai_settings(
    _: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return get_ai_configuration(session, settings)


@router.put("/api/hr/settings/ai")
def update_hr_ai_settings(
    request: AiConfigurationUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return update_ai_configuration(session, actor, settings, request)


@router.get("/api/hr/settings/questionnaire")
def hr_questionnaire_settings(
    _: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_questionnaire_settings(session)


@router.put("/api/hr/settings/questionnaire")
def update_hr_questionnaire_settings(
    request: QuestionnaireSettingsUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: update_questionnaire_settings(session, actor, request))
