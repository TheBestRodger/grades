from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..api.deps import get_database, get_session, get_settings
from ..features.settings.service import get_ai_configuration
from ..infrastructure.ai.gateway import build_local_gateway_from_configuration
from .config import Settings
from .db import Database

router = APIRouter()


@router.get("/api/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


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


def _readiness_payload(database: Database) -> dict[str, object]:
    try:
        with database.engine.connect() as connection:
            connection.execute(text("select 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": {"database": "error"}},
        ) from exc
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
        },
    }


@router.get("/api/health/ready")
def readiness(database: Database = Depends(get_database)) -> dict[str, object]:
    return _readiness_payload(database)


@router.get("/api/readiness")
def legacy_readiness(database: Database = Depends(get_database)) -> dict[str, object]:
    return _readiness_payload(database)
