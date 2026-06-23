from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def test_app(postgres_database_url: str, tmp_path: Path) -> FastAPI:
    from app.core.config import Settings
    from app.main import create_app
    from app.runtime_setup import prepare_runtime_database

    settings = Settings(
        app_name="Backend integration test app",
        app_env="test",
        ai_mode="off",
        ai_provider="off",
        ai_base_url=None,
        ai_model_name=None,
        ai_api_token=None,
        ai_request_timeout_seconds=1,
        database_url=postgres_database_url,
        frontend_dist=tmp_path / "missing-dist",
        work_staffing_file=None,
        document_storage_dir=tmp_path / "document_storage",
        auto_import_grades_documents=False,
    )
    prepare_runtime_database(settings)
    return create_app(settings)


@pytest.fixture()
def client(test_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture()
def demo_users(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/api/demo/users")
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def hr_user(demo_users: list[dict[str, Any]]) -> dict[str, Any]:
    return next(user for user in demo_users if user["role"] == "hr")


@pytest.fixture()
def employee_user(demo_users: list[dict[str, Any]]) -> dict[str, Any]:
    return next(user for user in demo_users if user["role"] == "employee")


@pytest.fixture()
def manager_user(demo_users: list[dict[str, Any]]) -> dict[str, Any]:
    return next(user for user in demo_users if user["role"] == "manager")


def demo_headers(user: dict[str, Any]) -> dict[str, str]:
    return {"X-Demo-User-Id": str(user["id"])}
