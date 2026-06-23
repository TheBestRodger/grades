from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


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
