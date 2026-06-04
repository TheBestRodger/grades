from __future__ import annotations

from datetime import UTC, datetime
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import AiConfiguration, AuditEvent, Employee
from .schemas import AiConfigurationUpdate


MODE_LABELS = {
    "default": "По умолчанию",
    "off": "ИИ отключён",
    "local": "Локальная ИИ",
    "token": "ИИ по токену",
}

PROVIDER_LABELS = {
    "off": "Без провайдера",
    "ollama": "Ollama",
    "lm_studio": "LM Studio",
    "openai_compatible": "OpenAI-compatible API",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _audit(
    session: Session,
    actor: Employee,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details_json=json.dumps(details, ensure_ascii=False),
        )
    )


def get_or_create_ai_configuration(session: Session) -> AiConfiguration:
    config = session.scalar(select(AiConfiguration).where(AiConfiguration.id == 1))
    if config is not None:
        return config
    config = AiConfiguration(id=1, mode="default", provider="off")
    session.add(config)
    session.flush()
    return config


def ai_configuration_payload(
    config: AiConfiguration,
    settings: Settings,
    include_secret: bool = False,
) -> dict[str, object]:
    effective_mode = settings.ai_mode if config.mode == "default" else config.mode
    effective_provider = settings.ai_provider if config.mode == "default" else config.provider
    effective_base_url = config.base_url or settings.ai_base_url
    effective_model_name = config.model_name or settings.ai_model_name
    effective_api_token = config.api_token or settings.ai_api_token
    is_configured = bool(
        effective_mode == "local"
        and effective_provider in {"ollama", "lm_studio"}
        and effective_base_url
        and effective_model_name
    ) or bool(
        effective_mode == "token"
        and effective_provider == "openai_compatible"
        and effective_base_url
        and effective_model_name
        and effective_api_token
    )
    is_llm_enabled = effective_mode != "off" and effective_provider != "off" and is_configured
    payload = {
        "mode": config.mode,
        "mode_label": MODE_LABELS.get(config.mode, config.mode),
        "provider": config.provider,
        "provider_label": PROVIDER_LABELS.get(config.provider, config.provider),
        "base_url": effective_base_url,
        "model_name": effective_model_name,
        "api_token_configured": bool(effective_api_token),
        "clarity_threshold": config.clarity_threshold,
        "followup_strictness": config.followup_strictness,
        "effective_mode": effective_mode,
        "effective_provider": effective_provider,
        "request_timeout_seconds": settings.ai_request_timeout_seconds,
        "available": is_llm_enabled,
        "connection_status": "configured" if is_llm_enabled else "not_configured",
        "note": (
            "LLM подключена. В модель передается только обезличенный контекст вопроса и ответа."
            if is_llm_enabled
            else (
                "LLM не настроена. Реальные вызовы не выполняются, "
                "персональные данные в модель не передаются."
            )
        ),
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        "updated_by_id": config.updated_by_id,
    }
    if include_secret:
        payload["api_token"] = effective_api_token
    return payload


def get_ai_configuration(
    session: Session,
    settings: Settings,
    include_secret: bool = False,
) -> dict[str, object]:
    return ai_configuration_payload(get_or_create_ai_configuration(session), settings, include_secret)


def update_ai_configuration(
    session: Session,
    actor: Employee,
    settings: Settings,
    request: AiConfigurationUpdate,
) -> dict[str, object]:
    config = get_or_create_ai_configuration(session)
    previous = ai_configuration_payload(config, settings)
    config.mode = request.mode
    config.provider = request.provider
    config.base_url = request.base_url
    config.model_name = request.model_name
    if request.clear_api_token:
        config.api_token = None
    elif request.api_token is not None:
        config.api_token = request.api_token
    if request.mode in {"default", "off", "local"} and request.provider != "openai_compatible":
        config.api_token = None
    config.updated_by_id = actor.id
    config.clarity_threshold = request.clarity_threshold
    config.followup_strictness = request.followup_strictness
    config.updated_at = _now()
    session.flush()
    current = ai_configuration_payload(config, settings)
    _audit(
        session,
        actor,
        "settings.ai_configuration_updated",
        "ai_configuration",
        config.id,
        {
            "previous": {
                "mode": previous["mode"],
                "provider": previous["provider"],
                "api_token_configured": previous["api_token_configured"],
            },
            "current": {
                "mode": current["mode"],
                "provider": current["provider"],
                "api_token_configured": current["api_token_configured"],
                "clarity_threshold": current["clarity_threshold"],
                "followup_strictness": current["followup_strictness"],
            },
        },
    )
    return current
