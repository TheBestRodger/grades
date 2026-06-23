from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
