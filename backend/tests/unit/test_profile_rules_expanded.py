from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.features.profiles.errors import ProfileOperationError
from app.features.profiles.questions import PROFILE_QUESTIONS
from app.features.profiles.rules import (
    AI_ANSWER_STATUS_ACCEPTED,
    AI_ANSWER_STATUS_FILLED_WITHOUT_AI,
    AI_ANSWER_STATUS_IGNORED,
    assistant_payload,
    default_answer_requirements,
    ensure_known_answer_keys,
    is_answer_filled,
    progress,
    question_with_settings,
    single_choice_labels,
    validate_answers,
    visible_org_path,
)
from app.features.profiles.schemas import ProfileAnswersRequest


def _single_choice_question() -> dict[str, object]:
    return next(question for question in PROFILE_QUESTIONS if question.get("input_type") == "single_choice")


def test_answer_fill_rules_cover_text_single_choice_and_tables() -> None:
    single_choice = _single_choice_question()
    valid_label = next(iter(single_choice_labels(single_choice)))

    assert not is_answer_filled({"input_type": "text"}, "   ")
    assert is_answer_filled({"input_type": "text"}, "Заполнено")
    assert is_answer_filled(single_choice, valid_label)
    assert not is_answer_filled(single_choice, "Несуществующий вариант")
    assert not is_answer_filled({"input_type": "table"}, json.dumps([["", "   "]]))
    assert is_answer_filled({"input_type": "table"}, json.dumps([["", "результат"]]))
    assert is_answer_filled({"input_type": "table"}, "not-json-yet")


def test_profile_answer_validation_rejects_unknown_keys_and_invalid_single_choice() -> None:
    single_choice = _single_choice_question()

    with pytest.raises(ProfileOperationError) as invalid_choice:
        validate_answers({str(single_choice["key"]): "Несуществующий вариант"})
    assert invalid_choice.value.status_code == 422

    with pytest.raises(ProfileOperationError):
        ensure_known_answer_keys(ProfileAnswersRequest(answers={"unknown_section": "value"}))


def test_assistant_payload_normalizes_ai_usage_and_legacy_statuses() -> None:
    request = ProfileAnswersRequest(
        ai_checked_questions=["position_purpose", "position_purpose", "unknown"],
        ai_ignored_questions=["position_purpose", "unknown"],
        ai_without_ai_questions=["comments", "unknown"],
        ai_answer_statuses={
            "position_purpose": "accepted",
            "comments": "without_ai",
        },
    )

    mode, assistance_level, raw_payload = assistant_payload(request, "off")
    payload = json.loads(raw_payload)

    assert mode == "ai_checked"
    assert assistance_level == AI_ANSWER_STATUS_IGNORED
    assert payload["checked_questions"] == ["position_purpose"]
    assert payload["ignored_questions"] == ["position_purpose"]
    assert payload["without_ai_questions"] == ["comments"]
    assert payload["answer_statuses"]["position_purpose"] == AI_ANSWER_STATUS_IGNORED
    assert payload["answer_statuses"]["comments"] == AI_ANSWER_STATUS_FILLED_WITHOUT_AI


def test_assistant_payload_falls_back_when_ai_was_not_used() -> None:
    assert assistant_payload(ProfileAnswersRequest(), "off") == ("off", "draft", "[]")
    assert assistant_payload(ProfileAnswersRequest(), "token") == ("token", "filled_without_ai", "[]")


def test_question_settings_and_progress_helpers_are_stable() -> None:
    text_question = next(question for question in PROFILE_QUESTIONS if question.get("input_type") == "textarea")
    table_question = {"input_type": "table", "question": "Какие результаты?", "example": "Пример"}
    setting = SimpleNamespace(
        good_example=" Хороший пример ",
        bad_example="Плохой пример",
        requirements="Особые требования",
        ai_check_enabled=False,
    )

    configured = question_with_settings(text_question, setting)

    assert visible_org_path("/WORK/Дирекция/Отдел") == "Дирекция / Отдел"
    assert default_answer_requirements(table_question) == "Заполните таблицу по смыслу вопроса и указанным строкам."
    assert configured["good_example"] == " Хороший пример "
    assert configured["requirements"] == "Особые требования"
    assert configured["ai_check_enabled"] is False
    assert progress({}) == 0
    assert progress({"position_purpose": "Делает процесс устойчивым."}) > 0
    assert AI_ANSWER_STATUS_ACCEPTED == "accepted"
