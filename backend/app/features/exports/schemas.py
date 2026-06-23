from __future__ import annotations

from pydantic import BaseModel, Field


class CredentialExportRow(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)
    role: str = Field(default="", max_length=50)
    position: str = Field(default="", max_length=255)


class CredentialsExportRequest(BaseModel):
    rows: list[CredentialExportRow] = Field(min_length=1, max_length=500)
