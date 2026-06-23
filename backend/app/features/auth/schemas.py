from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("Укажите корректный email.")
    return normalized


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
    username: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()
