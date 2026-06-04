from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .ai_gateway import AiGatewayError, OffProvider, OllamaProvider, OpenAICompatibleProvider
from .models import (
    Assignment,
    AuditEvent,
    CampaignParticipant,
    Employee,
    EmployeeProfile,
    StaffingLine,
)
from .profile_operations import QUESTION_KEYS, get_effective_profile_questions
from .schemas import AiProfileAnswerCheckRequest


class AiProfileCheckError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _audit(
    session: Session,
    actor: Employee,
    action: str,
    profile_id: int,
    details: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action=action,
            entity_type="employee_profile",
            entity_id=str(profile_id),
            details_json=json.dumps(details, ensure_ascii=False),
            created_at=_now(),
        )
    )


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
    profile = _get_owned_profile(session, actor, profile_id)
    question = next(
        item for item in get_effective_profile_questions(session) if item["key"] == request.question_key
    )
    if question["input_type"] == "single_choice":
        raise AiProfileCheckError("ИИ-уточнение доступно только для открытых вопросов.", 422)
    if not question.get("ai_check_enabled", True):
        raise AiProfileCheckError("ИИ-проверка отключена HR для этого вопроса анкеты.", 422)
    answer = request.answers.get(request.question_key, "").strip()
    if not answer:
        raise AiProfileCheckError("Сначала заполните ответ для проверки.", 422)

    payload = _build_payload(
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

    _audit(
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
    accepted = int(result.get("clarity_percent", 0)) >= clarity_threshold and result.get("status") == "accepted"
    return {
        "profile_id": profile.id,
        "question_key": request.question_key,
        "question_title": question["title"],
        "payload_policy": "anonymized_no_personal_data",
        "clarity_threshold": clarity_threshold,
        "accepted": accepted,
        **result,
    }


def _get_owned_profile(session: Session, actor: Employee, profile_id: int) -> EmployeeProfile:
    profile = session.scalar(
        select(EmployeeProfile)
        .join(EmployeeProfile.participant)
        .join(CampaignParticipant.assignment)
        .where(EmployeeProfile.id == profile_id, Assignment.employee_id == actor.id)
        .options(
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.campaign),
            selectinload(EmployeeProfile.participant)
            .selectinload(CampaignParticipant.assignment)
            .selectinload(Assignment.staffing_line)
            .selectinload(StaffingLine.org_unit),
        )
    )
    if profile is None:
        raise AiProfileCheckError("Профиль не найден или недоступен.", 404)
    return profile


def _build_payload(
    profile: EmployeeProfile,
    question: dict[str, Any],
    answer: str,
    request: AiProfileAnswerCheckRequest,
    clarity_threshold: int,
    followup_strictness: str,
) -> dict[str, object]:
    assignment = profile.participant.assignment
    line = assignment.staffing_line
    return {
        "interviewer_role": "HR assistant for position profiling",
        "clarity_threshold": clarity_threshold,
        "followup_strictness": followup_strictness,
        "position_title": line.title,
        "unit_context": _visible_org_path(line.org_unit.path),
        "question_key": question["key"],
        "section": question["section"],
        "question": question["question"],
        "requirements": _requirements_for_ai(question.get("requirements")),
        "example_answer": question.get("good_example") or question["example"],
        "bad_example": question.get("bad_example"),
        "current_answer": _flatten_answer(answer),
        "previous_answer": request.previous_answer,
        "previous_followup_question": request.previous_followup_question,
        "previous_clarity_percent": request.previous_clarity_percent,
    }


def _requirements_for_ai(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    text = re.split(r"\s*Добавьте\s+конкретику\s*:?", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return text or None


def _visible_org_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and part.upper() not in {"DEMO", "WORK"}]
    return " / ".join(parts)


def _flatten_answer(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, list):
        rows = []
        for row in parsed:
            if isinstance(row, list):
                text = " / ".join(cell.strip() for cell in row if isinstance(cell, str) and cell.strip())
                if text:
                    rows.append(text)
        return "; ".join(rows) or value
    return value
