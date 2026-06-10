from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...ai_gateway import build_local_gateway_from_configuration
from ...config import Settings
from ...settings_operations import get_ai_configuration
from ..deps import get_session, get_settings

router = APIRouter()


@router.get("/api/health")
def health(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    ai_config = get_ai_configuration(session, settings)
    runtime_ai_config = get_ai_configuration(session, settings, include_secret=True)
    runtime_ai_gateway = build_local_gateway_from_configuration(runtime_ai_config)
    ai = runtime_ai_gateway.health_status()
    return {
        "status": "ok",
        "environment": settings.app_env,
        "ai": {
            "mode": ai.mode,
            "provider": ai.provider,
            "available": ai.available,
            "label": ai.label,
            "fallback_message": ai.fallback_message,
            "configuration": ai_config,
        },
    }
