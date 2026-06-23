from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from backend.tests.fixtures.app import demo_headers


def test_public_health_and_demo_users_smoke(client: TestClient) -> None:
    liveness = client.get("/api/health/live")
    assert liveness.status_code == 200
    assert liveness.json() == {"status": "alive"}

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    readiness = client.get("/api/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["checks"]["database"] == "ok"

    legacy_readiness = client.get("/api/readiness")
    assert legacy_readiness.status_code == 200
    assert legacy_readiness.json() == readiness.json()

    demo_users = client.get("/api/demo/users")
    assert demo_users.status_code == 200
    users = demo_users.json()
    assert any(user["role"] == "hr" for user in users)
    assert any(user["role"] == "employee" for user in users)


def test_authenticated_demo_core_endpoints_smoke(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    hr_headers = demo_headers(hr_user)
    employee_headers = demo_headers(employee_user)

    me = client.get("/api/me", headers=hr_headers)
    assert me.status_code == 200
    assert me.json()["is_hr"] is True

    for path in (
        "/api/organization/summary",
        "/api/organization/tree",
        "/api/hr/managers",
        "/api/hr/campaigns",
        "/api/hr/documents",
        "/api/hr/analytics",
        "/api/hr/exports/profiles.json",
        "/api/hr/exports/campaigns.json",
        "/api/notifications",
        "/api/notifications/unread-count",
    ):
        response = client.get(path, headers=hr_headers)
        assert response.status_code == 200, path

    profiles = client.get("/api/my/profiles", headers=employee_headers)
    assert profiles.status_code == 200
    assert isinstance(profiles.json(), list)
