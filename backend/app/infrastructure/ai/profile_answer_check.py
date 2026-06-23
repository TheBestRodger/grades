from __future__ import annotations

import json
import re
from typing import Any

from ...models import EmployeeProfile
from ...features.profiles.schemas import AiProfileAnswerCheckRequest


def build_profile_answer_payload(
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
        "unit_context": visible_org_path(line.org_unit.path),
        "question_key": question["key"],
        "section": question["section"],
        "question": question["question"],
        "requirements": requirements_for_ai(question.get("requirements")),
        "example_answer": question.get("good_example") or question["example"],
        "bad_example": question.get("bad_example"),
        "current_answer": flatten_answer(answer),
        "previous_answer": request.previous_answer,
        "previous_followup_question": request.previous_followup_question,
        "previous_clarity_percent": request.previous_clarity_percent,
    }


def requirements_for_ai(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    text = re.split(r"\s*Добавьте\s+конкретику\s*:?", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return text or None


def visible_org_path(path: str) -> str:
    parts = [part for part in path.split("/") if part and part.upper() not in {"DEMO", "WORK"}]
    return " / ".join(parts)


def flatten_answer(value: str) -> str:
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


_build_payload = build_profile_answer_payload
_requirements_for_ai = requirements_for_ai
_visible_org_path = visible_org_path
_flatten_answer = flatten_answer
