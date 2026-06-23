from __future__ import annotations

import json

from ...models import EmployeeProfile
from .errors import ProfileOperationError
from .questions import (
    AI_CHECKABLE_QUESTION_KEYS,
    EDITABLE_STATUSES,
    LOCKED_PREFILLED_QUESTION_KEYS,
    PROFILE_QUESTIONS,
    QUESTION_KEYS,
    SYSTEM_QUESTION_KEYS,
)
from .schemas import ProfileAnswersRequest
from .time import now

AI_ANSWER_STATUS_DRAFT = "draft"
AI_ANSWER_STATUS_ACCEPTED = "accepted"
AI_ANSWER_STATUS_REJECTED = "rejected"
AI_ANSWER_STATUS_IGNORED = "ignored_ai"
AI_ANSWER_STATUS_FILLED_WITHOUT_AI = "filled_without_ai"

AI_ANSWER_STATUSES = {
    AI_ANSWER_STATUS_DRAFT,
    AI_ANSWER_STATUS_ACCEPTED,
    AI_ANSWER_STATUS_REJECTED,
    AI_ANSWER_STATUS_IGNORED,
    AI_ANSWER_STATUS_FILLED_WITHOUT_AI,
}

LEGACY_AI_ANSWER_STATUS_ALIASES = {
    "ignored": AI_ANSWER_STATUS_IGNORED,
    "without_ai": AI_ANSWER_STATUS_FILLED_WITHOUT_AI,
}


def normalize_ai_answer_status(status: str | None) -> str:
    if not status:
        return AI_ANSWER_STATUS_DRAFT
    normalized = LEGACY_AI_ANSWER_STATUS_ALIASES.get(status, status)
    return normalized if normalized in AI_ANSWER_STATUSES else AI_ANSWER_STATUS_DRAFT


def is_ai_answer_accepted(status: str | None) -> bool:
    return normalize_ai_answer_status(status) == AI_ANSWER_STATUS_ACCEPTED


def is_ai_answer_rejected(status: str | None) -> bool:
    return normalize_ai_answer_status(status) == AI_ANSWER_STATUS_REJECTED


def visible_org_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and part.upper() not in {"DEMO", "WORK"}]
    return " / ".join(parts)


def default_answer_requirements(question: dict[str, object]) -> str:
    if question["input_type"] == "table":
        return "Заполните таблицу по смыслу вопроса и указанным строкам."
    return (
        f"Ответ должен прямо отвечать на вопрос «{question['question']}». "
        f"Ориентир: {question['example']}"
    )


def question_with_settings(question: dict[str, object], setting: object | None) -> dict[str, object]:
    checkable = question["key"] in AI_CHECKABLE_QUESTION_KEYS
    configured_good_example = getattr(setting, "good_example", None) if setting else None
    configured_requirements = getattr(setting, "requirements", None) if setting else None
    return {
        **question,
        "example": configured_good_example or question["example"],
        "good_example": configured_good_example or question["example"],
        "bad_example": getattr(setting, "bad_example", None) if setting else None,
        "requirements": configured_requirements or default_answer_requirements(question),
        "ai_check_enabled": checkable and (getattr(setting, "ai_check_enabled", True) if setting else True),
    }


def prefilled_section_one_answers(profile: EmployeeProfile) -> dict[str, str]:
    assignment = profile.participant.assignment
    line = assignment.staffing_line
    unit = line.org_unit
    manager = assignment.manager
    manager_label = "Нет."
    if manager is not None:
        manager_line = manager.staffing_line
        manager_label = f"{manager_line.title} / {manager_line.org_unit.name}"

    direct_reports = len(assignment.reports)
    return {
        "position_name": line.title,
        "org_structure": visible_org_path(unit.path),
        "administrative_manager": manager_label,
        "functional_manager": "Совпадает.",
        "direct_admin_reports": f"{direct_reports} чел." if direct_reports else "Нет.",
        "total_reports": f"{direct_reports} чел." if direct_reports else "Нет.",
        "functional_reports": "Нет.",
        "completion_date": now().strftime("%d.%m.%Y"),
    }


def single_choice_labels(question: dict[str, object]) -> set[str]:
    return {
        str(option.get("label", ""))
        for option in question.get("options", [])
        if isinstance(option, dict)
    }


def is_answer_filled(question: dict[str, object], answer: str) -> bool:
    if not answer.strip():
        return False
    if question.get("input_type") == "single_choice":
        return answer in single_choice_labels(question)
    if question.get("input_type") != "table":
        return True
    try:
        rows = json.loads(answer)
    except json.JSONDecodeError:
        return True
    if not isinstance(rows, list):
        return False
    return any(
        isinstance(row, list)
        and any(isinstance(cell, str) and cell.strip() for cell in row)
        for row in rows
    )


def validate_answers(answers: dict[str, str]) -> None:
    invalid = [
        question["title"]
        for question in PROFILE_QUESTIONS
        if question.get("input_type") == "single_choice"
        and answers.get(question["key"], "").strip()
        and answers.get(question["key"], "") not in single_choice_labels(question)
    ]
    if invalid:
        raise ProfileOperationError(
            "Выберите допустимый вариант в полях: " + ", ".join(invalid) + ".",
            422,
        )


def progress(answers: dict[str, str]) -> float:
    completed = sum(
        1
        for question in PROFILE_QUESTIONS
        if question["key"] not in SYSTEM_QUESTION_KEYS
        if is_answer_filled(question, answers.get(question["key"], ""))
    )
    total = len(PROFILE_QUESTIONS) - len(SYSTEM_QUESTION_KEYS)
    return round(completed / total * 100, 2)


def ensure_known_answer_keys(request: ProfileAnswersRequest) -> None:
    unknown_keys = set(request.answers) - QUESTION_KEYS
    if unknown_keys:
        raise ProfileOperationError("Переданы неизвестные разделы анкеты.")


def assistant_payload(request: ProfileAnswersRequest, fallback_mode: str) -> tuple[str, str, str]:
    checked = [key for key in request.ai_checked_questions if key in QUESTION_KEYS]
    ignored = [key for key in request.ai_ignored_questions if key in QUESTION_KEYS and key in checked]
    without_ai = [
        key
        for key in request.ai_without_ai_questions
        if key in QUESTION_KEYS and key not in checked and key not in ignored
    ]
    used = bool(checked or without_ai)
    if not used:
        return fallback_mode, "draft" if fallback_mode == "off" else "filled_without_ai", "[]"

    has_rejected = any(
        normalize_ai_answer_status(request.ai_answer_statuses.get(key)) == AI_ANSWER_STATUS_REJECTED
        for key in checked
        if key not in ignored
    )
    if checked and len(ignored) == len(checked):
        assistance_level = AI_ANSWER_STATUS_IGNORED
    elif checked and not ignored and not without_ai and not has_rejected:
        assistance_level = AI_ANSWER_STATUS_ACCEPTED
    elif without_ai and not checked:
        assistance_level = AI_ANSWER_STATUS_FILLED_WITHOUT_AI
    else:
        assistance_level = "mixed"
    answer_statuses = {
        key: normalize_ai_answer_status(request.ai_answer_statuses.get(key, AI_ANSWER_STATUS_ACCEPTED))
        for key in checked
    }
    for key in ignored:
        answer_statuses[key] = AI_ANSWER_STATUS_IGNORED
    answer_statuses.update({key: AI_ANSWER_STATUS_FILLED_WITHOUT_AI for key in without_ai})
    return (
        "ai_checked",
        assistance_level,
        json.dumps(
            {
                "checked_questions": checked,
                "ignored_questions": ignored,
                "without_ai_questions": without_ai,
                "answer_statuses": answer_statuses,
            },
            ensure_ascii=False,
        ),
    )


_assistant_payload = assistant_payload
_ensure_known_answer_keys = ensure_known_answer_keys
_default_answer_requirements = default_answer_requirements
_is_answer_filled = is_answer_filled
_prefilled_section_one_answers = prefilled_section_one_answers
_progress = progress
_question_with_settings = question_with_settings
_validate_answers = validate_answers
_visible_org_path = visible_org_path
