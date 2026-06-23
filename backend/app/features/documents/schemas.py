from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
