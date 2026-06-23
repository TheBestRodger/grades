from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

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
    is_hr: bool = False
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


class EmployeeAssignmentUpdate(BaseModel):
    full_name: str = Field(min_length=3, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    system_role: Literal["employee", "manager"] = "employee"
    is_hr: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class WorkStaffingEmployeeCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    fte: float = Field(default=1.0, gt=0, le=10)
    system_role: Literal["employee", "manager"] = "employee"
    is_hr: bool = False
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
