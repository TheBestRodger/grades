from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("Укажите корректный email.")
    return normalized


class EmployeeAssignmentCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    fte: float = Field(default=1.0, gt=0, le=10)
    system_role: Literal["employee", "manager"] = "employee"
    manager_assignment_id: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class BulkEmployeeCreate(BaseModel):
    employees: list[EmployeeAssignmentCreate] = Field(min_length=1, max_length=50)


class WorkStaffingEmployeeCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    fte: float = Field(default=1.0, gt=0, le=10)
    system_role: Literal["employee", "manager"] = "employee"
    manager_assignment_id: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class WorkStaffingLineCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    approved_fte: float = Field(gt=0, le=100)
    employees: list[WorkStaffingEmployeeCreate] = Field(default_factory=list, max_length=50)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return " ".join(value.split())


class MagicLinkRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class MagicLinkConsumeRequest(BaseModel):
    token: str = Field(min_length=20, max_length=255)

    @field_validator("token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        return value.strip()


class PasswordLoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class CredentialExportRow(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)
    role: str = Field(default="", max_length=50)
    position: str = Field(default="", max_length=255)


class CredentialsExportRequest(BaseModel):
    rows: list[CredentialExportRow] = Field(min_length=1, max_length=500)


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


class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    due_at: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class CampaignWaveCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    due_at: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class CampaignAssignmentsUpdate(BaseModel):
    assignment_ids: list[int] = Field(min_length=1, max_length=1000)
    action: Literal["include", "exclude"]

    @field_validator("assignment_ids")
    @classmethod
    def unique_assignment_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Список назначений содержит дубли.")
        return value


class WorkDocumentLinkUpdate(BaseModel):
    staffing_line_id: int
    document_type: str
    document_id: int | None = None

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, value: str) -> str:
        allowed = {"job_instruction", "unit_regulation", "professional_standard"}
        if value not in allowed:
            raise ValueError("Неизвестный тип документа.")
        return value


class WorkDocumentQualityUpdate(BaseModel):
    ocr_quality_status: Literal["good", "warning"]
    extracted_text: str = Field(default="", max_length=1_000_000)

    @field_validator("extracted_text")
    @classmethod
    def normalize_extracted_text(cls, value: str) -> str:
        return value.strip()


class ProfileAnswersRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    ai_checked_questions: list[str] = Field(default_factory=list, max_length=100)
    ai_ignored_questions: list[str] = Field(default_factory=list, max_length=100)
    ai_without_ai_questions: list[str] = Field(default_factory=list, max_length=100)
    ai_answer_statuses: dict[str, Literal["accepted", "ignored", "rejected", "without_ai"]] = Field(default_factory=dict)

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
        value: dict[str, Literal["accepted", "ignored", "rejected", "without_ai"]],
    ) -> dict[str, Literal["accepted", "ignored", "rejected", "without_ai"]]:
        return {key.strip(): status for key, status in value.items() if key.strip()}


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


class ReviewReturnRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return " ".join(value.split())


class BulkReviewReturnRequest(ReviewReturnRequest):
    profile_ids: list[int] = Field(default_factory=list, max_length=1000)
    org_unit_id: int | None = None

    @field_validator("profile_ids")
    @classmethod
    def unique_profile_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Список профилей содержит дубли.")
        return value

    @model_validator(mode="after")
    def require_single_selection(self) -> "BulkReviewReturnRequest":
        has_profiles = bool(self.profile_ids)
        has_unit = self.org_unit_id is not None
        if has_profiles == has_unit:
            raise ValueError("Выберите профили или подразделение для массового возврата.")
        return self


class ReviewVerifyRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None
