from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...ai_gateway import build_local_gateway_from_configuration
from ...ai_profile_checks import assess_profile_answer
from ...config import Settings
from ...models import Employee
from ...profile_operations import get_my_profiles, save_draft, submit_profile
from ...schemas import AiProfileAnswerCheckRequest, ProfileAnswersRequest
from ...settings_operations import get_ai_configuration
from ..deps import current_actor, get_ai_gateway, get_session, get_settings
from ..errors import run_operation

router = APIRouter()


@router.post("/api/my/profiles/{profile_id}/ai-check")
def ai_check_profile_answer(
    profile_id: int,
    request_payload: AiProfileAnswerCheckRequest,
    request: Request,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    ai_config = get_ai_configuration(session, settings, include_secret=True)
    gateway = build_local_gateway_from_configuration(
        ai_config,
        generate=getattr(request.app.state, "ollama_generate", None),
    )
    return run_operation(
        lambda: assess_profile_answer(
            session,
            actor,
            profile_id,
            request_payload,
            gateway,
            int(ai_config.get("clarity_threshold", 70)),
            str(ai_config.get("followup_strictness", "balanced")),
        )
    )


@router.get("/api/my/profiles")
def profiles(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    return get_my_profiles(session, actor)


@router.put("/api/my/profiles/{profile_id}/draft")
def update_draft(
    profile_id: int,
    request: ProfileAnswersRequest,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
    ai_gateway: Any = Depends(get_ai_gateway),
) -> dict[str, object]:
    return run_operation(
        lambda: save_draft(
            session, actor, profile_id, request, ai_gateway.health_status().mode
        )
    )


@router.post("/api/my/profiles/{profile_id}/submit")
def submit_personal_profile(
    profile_id: int,
    request: ProfileAnswersRequest,
    actor: Employee = Depends(current_actor),
    session: Session = Depends(get_session),
    ai_gateway: Any = Depends(get_ai_gateway),
) -> dict[str, object]:
    return run_operation(
        lambda: submit_profile(
            session, actor, profile_id, request, ai_gateway.health_status().mode
        )
    )
