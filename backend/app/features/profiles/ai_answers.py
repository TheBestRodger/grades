from __future__ import annotations

from sqlalchemy.orm import Session

from ...infrastructure.ai.gateway import (
    AiGatewayError,
    OffProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
)
from ...infrastructure.ai.profile_answer_check import build_profile_answer_payload
from ...models import Employee
from .schemas import AiProfileAnswerCheckRequest
from .audit import audit_profile_event
from .errors import AiProfileCheckError
from .questionnaire import get_effective_profile_questions
from .repository import load_owned_profile
from .rules import QUESTION_KEYS


def assess_profile_answer(
    session: Session,
    actor: Employee,
    profile_id: int,
    request: AiProfileAnswerCheckRequest,
    gateway: OffProvider | OllamaProvider | OpenAICompatibleProvider,
    clarity_threshold: int,
    followup_strictness: str,
) -> dict[str, object]:
    if request.question_key not in QUESTION_KEYS:
        raise AiProfileCheckError("Неизвестный вопрос анкеты.", 422)
    profile = load_owned_profile(session, actor, profile_id)
    if profile is None:
        raise AiProfileCheckError("Профиль не найден или недоступен.", 404)
    question = next(
        item
        for item in get_effective_profile_questions(session)
        if item["key"] == request.question_key
    )
    if question["input_type"] == "single_choice":
        raise AiProfileCheckError(
            "ИИ-уточнение доступно только для открытых вопросов.", 422
        )
    if not question.get("ai_check_enabled", True):
        raise AiProfileCheckError(
            "ИИ-проверка отключена HR для этого вопроса анкеты.", 422
        )
    answer = request.answers.get(request.question_key, "").strip()
    if not answer:
        raise AiProfileCheckError("Сначала заполните ответ для проверки.", 422)

    payload = build_profile_answer_payload(
        profile,
        question,
        answer,
        request,
        clarity_threshold,
        followup_strictness,
    )
    try:
        result = gateway.assess_profile_answer(payload)
    except AiGatewayError as exc:
        raise AiProfileCheckError(exc.message, exc.status_code) from exc
    except Exception as exc:
        raise AiProfileCheckError(
            "ИИ-помощник временно недоступен. Повторите позже.", 503
        ) from exc

    audit_profile_event(
        session,
        actor,
        "profile.ai_answer_checked",
        profile.id,
        {
            "question_key": request.question_key,
            "provider": result.get("provider"),
            "model": result.get("model"),
            "clarity_percent": result.get("clarity_percent"),
            "status": result.get("status"),
            "clarity_threshold": clarity_threshold,
            "pii_policy": "no_employee_name_email_or_external_ids",
        },
    )
    accepted = (
        int(result.get("clarity_percent", 0)) >= clarity_threshold
        and result.get("status") == "accepted"
    )
    if accepted:
        result["followup_question"] = ""
    return {
        "profile_id": profile.id,
        "question_key": request.question_key,
        "question_title": question["title"],
        "payload_policy": "anonymized_no_personal_data",
        "clarity_threshold": clarity_threshold,
        "accepted": accepted,
        **result,
    }
