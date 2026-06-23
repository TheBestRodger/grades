from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AiConfigurationUpdate(BaseModel):
    mode: Literal["default", "off", "local", "token"] = "default"
    provider: Literal["off", "ollama", "lm_studio", "openai_compatible"] = "off"
    base_url: str | None = Field(default=None, max_length=500)
    model_name: str | None = Field(default=None, max_length=255)
    api_token: str | None = Field(default=None, max_length=1000)
    clear_api_token: bool = False
    clarity_threshold: int = Field(default=70, ge=0, le=100)
    followup_strictness: Literal["soft", "balanced", "strict"] = "balanced"

    @field_validator("base_url", "model_name", "api_token")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_provider(self) -> "AiConfigurationUpdate":
        if self.mode in {"default", "off"} and self.provider != "off":
            raise ValueError("Для режима по умолчанию или без ИИ провайдер должен быть off.")
        if self.mode == "local" and self.provider not in {"ollama", "lm_studio"}:
            raise ValueError("Для локальной ИИ выберите Ollama или LM Studio.")
        if self.mode == "token" and self.provider != "openai_compatible":
            raise ValueError("Для режима по токену используйте OpenAI-compatible провайдер.")
        return self


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
