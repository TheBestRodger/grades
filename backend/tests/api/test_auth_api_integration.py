from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.features.auth.passwords import hash_password
from app.models import Employee
from backend.tests.fixtures.app import demo_headers


def test_magic_link_consume_logout_and_revoked_session_access(
    client: TestClient,
    hr_user: dict[str, Any],
) -> None:
    request_response = client.post(
        "/api/auth/magic-link/request",
        json={"email": hr_user["email"]},
    )
    assert request_response.status_code == 200
    login_token = request_response.json()["login_token"]
    assert login_token

    consume_response = client.post(
        "/api/auth/magic-link/consume",
        json={"token": login_token},
    )
    assert consume_response.status_code == 200
    session_token = consume_response.json()["token"]

    auth_headers = {"Authorization": f"Bearer {session_token}"}
    me_response = client.get("/api/me", headers=auth_headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == hr_user["email"]

    logout_response = client.post("/api/auth/logout", headers=auth_headers)
    assert logout_response.status_code == 200
    assert logout_response.json() == {"revoked": True}

    revoked_response = client.get("/api/me", headers=auth_headers)
    assert revoked_response.status_code == 401


def test_password_login_and_hr_access_denies_for_employee(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    with client.app.state.database.session() as session:
        hr = session.scalar(select(Employee).where(Employee.id == hr_user["id"]))
        assert hr is not None
        hr.username = "b10_hr"
        hr.password_hash = hash_password("b10-password")

    login_response = client.post(
        "/api/auth/login",
        json={"username": "b10_hr", "password": "b10-password"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["is_hr"] is True

    denied_response = client.get(
        "/api/hr/campaigns",
        headers=demo_headers(employee_user),
    )
    assert denied_response.status_code == 403


def test_pilot_magic_link_response_does_not_expose_token(
    client: TestClient,
    hr_user: dict[str, Any],
    monkeypatch,
) -> None:
    sent_links: list[tuple[str, str]] = []

    def fake_send_magic_link_email(settings, recipient_email: str, login_url: str) -> None:
        sent_links.append((recipient_email, login_url))

    monkeypatch.setattr("app.features.auth.email.send_magic_link_email", fake_send_magic_link_email)
    client.app.state.settings = replace(
        client.app.state.settings,
        app_env="pilot",
        smtp_host="smtp.test.local",
        smtp_from_email="noreply@test.local",
    )

    response = client.post(
        "/api/auth/magic-link/request",
        json={"email": hr_user["email"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["delivery_mode"] == "email"
    assert payload["login_token"] is None
    assert payload["login_url"] is None
    assert sent_links and sent_links[0][0] == hr_user["email"]
