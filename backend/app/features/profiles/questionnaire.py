from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...models import AuditEvent, Employee, QuestionnaireQuestionSetting
from .schemas import QuestionnaireSettingsUpdate
from . import repository
from .rules import (
    AI_CHECKABLE_QUESTION_KEYS,
    PROFILE_QUESTIONS,
    ProfileOperationError,
    _default_answer_requirements,
)
from .time import now


def question_settings_by_key(session: Session) -> dict[str, QuestionnaireQuestionSetting]:
    return {setting.question_key: setting for setting in repository.load_question_settings(session)}


def question_with_settings(
    question: dict[str, object],
    setting: QuestionnaireQuestionSetting | None,
) -> dict[str, object]:
    checkable = question["key"] in AI_CHECKABLE_QUESTION_KEYS
    configured_good_example = setting.good_example if setting else None
    configured_requirements = setting.requirements if setting else None
    return {
        **question,
        "example": configured_good_example or question["example"],
        "good_example": configured_good_example or question["example"],
        "bad_example": setting.bad_example if setting else None,
        "requirements": configured_requirements or _default_answer_requirements(question),
        "ai_check_enabled": checkable and (setting.ai_check_enabled if setting else True),
    }


def get_effective_profile_questions(session: Session) -> list[dict[str, object]]:
    settings = question_settings_by_key(session)
    return [
        question_with_settings(question, settings.get(str(question["key"])))
        for question in PROFILE_QUESTIONS
    ]


def get_questionnaire_settings(session: Session) -> dict[str, object]:
    settings = question_settings_by_key(session)
    questions = []
    for question in PROFILE_QUESTIONS:
        if question["key"] not in AI_CHECKABLE_QUESTION_KEYS:
            continue
        setting = settings.get(str(question["key"]))
        effective = question_with_settings(question, setting)
        questions.append(
            {
                "question_key": question["key"],
                "section": question["section"],
                "title": question["title"],
                "input_type": question["input_type"],
                "question": question["question"],
                "base_example": question["example"],
                "ai_check_enabled": effective["ai_check_enabled"],
                "good_example": effective["good_example"],
                "bad_example": effective["bad_example"],
                "requirements": effective["requirements"],
                "updated_at": setting.updated_at.isoformat() if setting and setting.updated_at else None,
                "updated_by_id": setting.updated_by_id if setting else None,
            }
        )
    return {
        "scope": "global_current_questionnaire",
        "versioning_status": "not_versioned_yet",
        "questions": questions,
    }


def update_questionnaire_settings(
    session: Session,
    actor: Employee,
    request: QuestionnaireSettingsUpdate,
) -> dict[str, object]:
    incoming_keys = {item.question_key for item in request.questions}
    unknown_keys = incoming_keys - AI_CHECKABLE_QUESTION_KEYS
    if unknown_keys:
        raise ProfileOperationError("Настраивать можно только открытые вопросы анкеты.", 422)

    existing = question_settings_by_key(session)
    changed = []
    for item in request.questions:
        setting = existing.get(item.question_key)
        if setting is None:
            setting = QuestionnaireQuestionSetting(question_key=item.question_key)
            session.add(setting)
        setting.ai_check_enabled = item.ai_check_enabled
        setting.good_example = item.good_example
        setting.bad_example = item.bad_example
        setting.requirements = item.requirements
        setting.updated_by_id = actor.id
        setting.updated_at = now()
        changed.append(item.question_key)
    session.flush()
    session.add(
        AuditEvent(
            actor_employee_id=actor.id,
            action="settings.questionnaire_answers_updated",
            entity_type="questionnaire_settings",
            entity_id="current",
            details_json=json.dumps(
                {
                    "changed_question_keys": changed,
                    "policy": "global_settings_before_questionnaire_versioning",
                },
                ensure_ascii=False,
            ),
        )
    )
    return get_questionnaire_settings(session)


_question_settings_by_key = question_settings_by_key
_question_with_settings = question_with_settings
