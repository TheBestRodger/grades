from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ProfileAnswerStatus = Literal[
    "accepted",
    "rejected",
    "ignored",
    "without_ai",
    "ignored_ai",
    "filled_without_ai",
]


class ProfileAnswersRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    ai_checked_questions: list[str] = Field(default_factory=list, max_length=100)
    ai_ignored_questions: list[str] = Field(default_factory=list, max_length=100)
    ai_without_ai_questions: list[str] = Field(default_factory=list, max_length=100)
    ai_answer_statuses: dict[str, ProfileAnswerStatus] = Field(default_factory=dict)

    @field_validator("answers")
    @classmethod
    def normalize_answers(cls, value: dict[str, str]) -> dict[str, str]:
        return {key: answer.strip() for key, answer in value.items()}

    @field_validator("ai_checked_questions", "ai_ignored_questions", "ai_without_ai_questions")
    @classmethod
    def normalize_ai_question_keys(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            key = item.strip()
            if key and key not in normalized:
                normalized.append(key)
        return normalized

    @field_validator("ai_answer_statuses")
    @classmethod
    def normalize_ai_answer_statuses(
        cls,
        value: dict[str, ProfileAnswerStatus],
    ) -> dict[str, str]:
        normalized: dict[str, str] = {}
        mapping = {
            "ignored": "ignored_ai",
            "without_ai": "filled_without_ai",
        }
        for key, status in value.items():
            normalized_key = key.strip()
            if not normalized_key:
                continue
            normalized[normalized_key] = mapping.get(status, status)
        return normalized


class AiProfileAnswerCheckRequest(ProfileAnswersRequest):
    question_key: str = Field(min_length=1, max_length=100)
    previous_answer: str | None = Field(default=None, max_length=20_000)
    previous_followup_question: str | None = Field(default=None, max_length=2000)
    previous_clarity_percent: int | None = Field(default=None, ge=0, le=100)

    @field_validator("question_key")
    @classmethod
    def normalize_question_key(cls, value: str) -> str:
        return value.strip()

    @field_validator("previous_answer", "previous_followup_question")
    @classmethod
    def normalize_optional_ai_context(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class QuestionnaireQuestionSettingUpdate(BaseModel):
    question_key: str = Field(min_length=1, max_length=100)
    ai_check_enabled: bool = True
    good_example: str | None = Field(default=None, max_length=4000)
    bad_example: str | None = Field(default=None, max_length=4000)
    requirements: str | None = Field(default=None, max_length=4000)

    @field_validator("question_key")
    @classmethod
    def normalize_question_key(cls, value: str) -> str:
        return value.strip()

    @field_validator("good_example", "bad_example", "requirements")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class QuestionnaireSettingsUpdate(BaseModel):
    questions: list[QuestionnaireQuestionSettingUpdate] = Field(min_length=1, max_length=100)

    @field_validator("questions")
    @classmethod
    def unique_question_keys(
        cls,
        value: list[QuestionnaireQuestionSettingUpdate],
    ) -> list[QuestionnaireQuestionSettingUpdate]:
        keys = [item.question_key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("Список вопросов содержит дубли.")
        return value
