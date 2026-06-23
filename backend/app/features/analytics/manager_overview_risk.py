from __future__ import annotations

import json

from ...models import ProfileRevision


RISK_LABELS = {
    "normal": "Норма",
    "attention": "Есть вопросы",
    "critical": "Красный сигнал",
}

STATUS_LABELS = {
    "not_started": "Не начат",
    "draft": "Черновик",
    "submitted": "Ожидает проверки",
    "under_review": "На проверке",
    "returned_for_revision": "На доработке",
    "manager_verified": "Подтвержден",
    "returned_by_hr": "Вернул HR",
    "hr_accepted": "Принят HR",
}


def revision_payload(revision: ProfileRevision | None) -> dict[str, object] | None:
    if revision is None:
        return None
    answers = _json_dict(revision.answers_json)
    assisted = _assisted_sections(revision.assisted_sections_json)
    return {
        "id": revision.id,
        "revision_no": revision.revision_no,
        "submitted_at": revision.submitted_at.isoformat(),
        "assistant_mode": revision.assistant_mode,
        "assistance_level": revision.assistance_level,
        "assisted_sections": {
            "checked_questions": assisted.get("checked_questions", []),
            "ignored_questions": assisted.get("ignored_questions", []),
            "without_ai_questions": assisted.get("without_ai_questions", []),
            "answer_statuses": assisted.get("answer_statuses", {}),
        },
        "answers": answers,
    }


def combined_risk(
    workflow_risk_level: str,
    workflow_reason: str,
    document_signal: dict[str, object],
) -> tuple[str, str]:
    document_risk = str(document_signal["risk_level"])
    if document_risk == "critical":
        return "critical", f"Документы: {document_signal['risk_reason']}"
    if workflow_risk_level == "critical":
        return "critical", workflow_reason
    return workflow_risk_level, workflow_reason


def workflow_risk(status: str, progress_percent: float, return_count: int) -> tuple[str, str]:
    if status == "returned_by_hr":
        return "critical", "HR вернул профиль руководителю."
    if return_count >= 2:
        return "critical", "Есть повторные возвраты, стоит разобрать причину."
    if status == "not_started":
        return "critical", "Профиль еще не начат в активной кампании."
    if progress_percent < 50:
        return "critical", "Заполнено меньше половины обязательных разделов."
    if status in {"draft", "submitted", "under_review", "returned_for_revision"}:
        return "attention", "Профиль требует внимания или решения руководителя."
    if return_count == 1:
        return "attention", "Был возврат на уточнение."
    return "normal", "Сильных сигналов нет."


def heat_level(quality_score: float) -> str:
    if quality_score >= 1:
        return "green"
    if quality_score >= 0.5:
        return "yellow"
    return "red"


def heat_label(level: str) -> str:
    return {
        "green": "100% без сигналов",
        "yellow": "Есть вопросы",
        "red": "Требует разбора",
    }[level]


def _json_dict(raw_value: str | None) -> dict[str, object]:
    try:
        parsed = json.loads(raw_value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _assisted_sections(raw_value: str | None) -> dict[str, object]:
    try:
        parsed = json.loads(raw_value or "{}")
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, list):
        return {"checked_questions": parsed, "ignored_questions": [], "without_ai_questions": []}
    return parsed if isinstance(parsed, dict) else {}

