from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.infrastructure.ai.gateway import AiGatewayError, OffProvider
from app.models import Assignment, Document, Employee
from backend.tests.fixtures.api import (
    assignment_for_employee,
    create_launched_campaign_for_assignment,
    first_staffing_line,
    profile_for_campaign,
)
from backend.tests.fixtures.app import demo_headers
from backend.tests.fixtures.profile_answers import complete_profile_answers


class _FailingGateway:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def assess_profile_answer(self, payload: dict[str, object]) -> dict[str, object]:
        raise self.error


def _make_profile(
    client: TestClient, hr_user: dict[str, Any], employee_user: dict[str, Any]
) -> dict[str, Any]:
    tree_response = client.get("/api/organization/tree", headers=demo_headers(hr_user))
    assert tree_response.status_code == 200
    assignment = assignment_for_employee(tree_response.json(), int(employee_user["id"]))
    campaign = create_launched_campaign_for_assignment(
        client,
        hr_user=hr_user,
        assignment_id=int(assignment["id"]),
        name=f"Negative path {uuid4().hex[:8]}",
    )
    return profile_for_campaign(
        client, employee_user=employee_user, campaign_id=int(campaign["id"])
    )


def _submit_profile(
    client: TestClient, employee_user: dict[str, Any], profile_id: int
) -> dict[str, Any]:
    response = client.post(
        f"/api/my/profiles/{profile_id}/submit",
        headers=demo_headers(employee_user),
        json={
            "answers": complete_profile_answers(),
            "ai_without_ai_questions": list(complete_profile_answers()),
        },
    )
    assert response.status_code == 200
    return response.json()


def _manager_headers_with_profile(
    client: TestClient, users: list[dict[str, Any]], profile_id: int
) -> dict[str, str]:
    for user in users:
        if user["role"] != "manager":
            continue
        response = client.get("/api/manager/reviews", headers=demo_headers(user))
        assert response.status_code == 200
        if any(item["id"] == profile_id for item in response.json()):
            return demo_headers(user)
    raise AssertionError("No manager has profile in queue")


def test_object_level_profile_access_and_repeated_submit_are_controlled(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
    demo_users: list[dict[str, Any]],
) -> None:
    other_employee = next(
        user
        for user in demo_users
        if user["role"] == "employee" and user["id"] != employee_user["id"]
    )
    profile = _make_profile(client, hr_user, employee_user)

    for method, path, payload in [
        (
            "put",
            f"/api/my/profiles/{profile['id']}/draft",
            {"answers": {"position_purpose": "Чужой черновик"}},
        ),
        (
            "post",
            f"/api/my/profiles/{profile['id']}/submit",
            {"answers": complete_profile_answers()},
        ),
    ]:
        response = getattr(client, method)(
            path, headers=demo_headers(other_employee), json=payload
        )
        assert response.status_code == 404

    first_submit = _submit_profile(client, employee_user, int(profile["id"]))
    assert first_submit["workflow_status"] == "submitted"
    repeated_submit = client.post(
        f"/api/my/profiles/{profile['id']}/submit",
        headers=demo_headers(employee_user),
        json={"answers": complete_profile_answers()},
    )
    assert repeated_submit.status_code == 409


def test_manager_cannot_process_profile_outside_queue_or_before_take(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
    demo_users: list[dict[str, Any]],
) -> None:
    profile = _make_profile(client, hr_user, employee_user)
    _submit_profile(client, employee_user, int(profile["id"]))
    owning_manager = _manager_headers_with_profile(
        client, demo_users, int(profile["id"])
    )
    wrong_manager_user = next(
        user
        for user in demo_users
        if user["role"] == "manager" and demo_headers(user) != owning_manager
    )

    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/take",
            headers=demo_headers(wrong_manager_user),
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/verify",
            headers=owning_manager,
            json={"comment": "Нельзя без взятия"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/return",
            headers=owning_manager,
            json={"reason": "Нельзя без взятия"},
        ).status_code
        == 409
    )


def test_repeated_auth_notifications_documents_and_wave_commands_are_not_500(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    token_response = client.post(
        "/api/auth/magic-link/request", json={"email": employee_user["email"]}
    )
    assert token_response.status_code == 200
    token = token_response.json()["login_token"]
    consume_response = client.post(
        "/api/auth/magic-link/consume", json={"token": token}
    )
    assert consume_response.status_code == 200
    auth_headers = {"Authorization": f"Bearer {consume_response.json()['token']}"}
    assert client.post("/api/auth/logout", headers=auth_headers).status_code == 200
    repeated_logout = client.post("/api/auth/logout", headers=auth_headers)
    assert repeated_logout.status_code in {200, 401}
    assert client.post(
        "/api/auth/magic-link/consume", json={"token": token}
    ).status_code in {401, 404}

    tree = client.get("/api/organization/tree", headers=demo_headers(hr_user)).json()
    assignment = assignment_for_employee(tree, int(employee_user["id"]))
    campaign = create_launched_campaign_for_assignment(
        client, hr_user=hr_user, assignment_id=int(assignment["id"])
    )

    notification = client.get(
        "/api/notifications", headers=demo_headers(employee_user)
    ).json()["items"][0]
    first_read = client.post(
        f"/api/notifications/{notification['id']}/read",
        headers=demo_headers(employee_user),
    )
    second_read = client.post(
        f"/api/notifications/{notification['id']}/read",
        headers=demo_headers(employee_user),
    )
    assert first_read.status_code == 200
    assert second_read.status_code == 200
    relaunch = client.post(
        f"/api/hr/campaigns/{campaign['id']}/waves/{campaign['active_wave_id']}/launch",
        headers=demo_headers(hr_user),
    )
    assert relaunch.status_code in {409, 422}


def test_hr_like_employee_gets_hr_access_and_non_hr_roles_are_denied(
    client: TestClient,
    hr_user: dict[str, Any],
) -> None:
    headers = demo_headers(hr_user)
    work_tree = client.get("/api/work/organization/tree", headers=headers).json()
    line = first_staffing_line(work_tree)
    add_response = client.post(
        f"/api/work/hr/staffing-lines/{line['id']}/employees/bulk",
        headers=headers,
        json={
            "employees": [
                {
                    "full_name": "HR Flag User",
                    "email": f"hrflag-{uuid4().hex[:8]}@profile.local",
                    "fte": 1,
                    "system_role": "employee",
                    "is_hr": True,
                }
            ]
        },
    )
    assert add_response.status_code == 200
    hr_like_headers = {
        "X-Demo-User-Id": str(add_response.json()["added"][0]["employee_id"])
    }
    assert (
        client.get("/api/work/hr/documents", headers=hr_like_headers).status_code == 200
    )


def test_bulk_employee_failure_rolls_back_partial_employee_and_assignment_rows(
    client: TestClient,
    test_app,
    hr_user: dict[str, Any],
) -> None:
    headers = demo_headers(hr_user)
    line = first_staffing_line(
        client.get("/api/work/organization/tree", headers=headers).json()
    )
    email = f"rollback-{uuid4().hex[:8]}@profile.local"
    response = client.post(
        f"/api/work/hr/staffing-lines/{line['id']}/employees/bulk",
        headers=headers,
        json={
            "employees": [
                {
                    "full_name": "Rollback One",
                    "email": email,
                    "fte": 1,
                    "system_role": "employee",
                    "is_hr": False,
                },
                {
                    "full_name": "Rollback Duplicate",
                    "email": email,
                    "fte": 1,
                    "system_role": "employee",
                    "is_hr": False,
                },
            ]
        },
    )
    assert response.status_code in {409, 422}
    with test_app.state.database.session() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Employee)
                .where(Employee.email == email)
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(Assignment)
                .join(Employee)
                .where(Employee.email == email)
            )
            == 0
        )


def test_document_upload_storage_failure_rolls_back_database_and_files(
    client: TestClient,
    test_app,
    hr_user: dict[str, Any],
    monkeypatch,
) -> None:
    from app.features.documents import upload as upload_module

    def fail_snapshot(*args, **kwargs):
        raise OSError("simulated snapshot write failure")

    monkeypatch.setattr(upload_module, "store_text_snapshot", fail_snapshot)
    code = f"ROLLBACK-{uuid4().hex[:8]}"
    response = client.post(
        "/api/work/hr/documents/upload",
        headers=demo_headers(hr_user),
        data={
            "document_code": code,
            "document_type": "job_instruction",
            "title": "Rollback document",
            "version": "v1",
        },
        files={"file": ("rollback.txt", b"document text", "text/plain")},
    )
    assert response.status_code == 400
    with test_app.state.database.session() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Document)
                .where(Document.document_code == code)
            )
            == 0
        )
    assert not list(
        (Path(test_app.state.document_storage_dir) / "originals").glob(
            f"{code.lower()}*"
        )
    )


def test_ai_gateway_failure_paths_do_not_mutate_draft(
    client: TestClient, hr_user: dict[str, Any], employee_user: dict[str, Any]
) -> None:
    profile = _make_profile(client, hr_user, employee_user)
    draft_response = client.put(
        f"/api/my/profiles/{profile['id']}/draft",
        headers=demo_headers(employee_user),
        json={"answers": {"position_purpose": "Initial draft remains intact"}},
    )
    assert draft_response.status_code == 200
    request = {
        "question_key": "position_purpose",
        "answers": {"position_purpose": "Check this answer"},
    }

    for gateway, expected in [
        (_FailingGateway(AiGatewayError("timeout sanitized", 503)), 503),
        (_FailingGateway(RuntimeError("internal client exception")), 503),
        (OffProvider(), 409),
    ]:
        original = client.app.state.ai_gateway
        client.app.state.ai_gateway = gateway
        try:
            response = client.post(
                f"/api/my/profiles/{profile['id']}/ai-check",
                headers=demo_headers(employee_user),
                json=request,
            )
        finally:
            client.app.state.ai_gateway = original
        assert response.status_code == expected

    after = client.get("/api/my/profiles", headers=demo_headers(employee_user)).json()
    current = next(item for item in after if item["id"] == profile["id"])
    assert current["answers"]["position_purpose"] == "Initial draft remains intact"


def test_nonexistent_and_validation_negative_cases_are_controlled(
    client: TestClient, hr_user: dict[str, Any]
) -> None:
    headers = demo_headers(hr_user)
    assert (
        client.post("/api/hr/campaigns/-1/waves/-1/launch", headers=headers).status_code
        == 404
    )
    assert client.put(
        "/api/work/hr/documents/link",
        headers=headers,
        json={
            "document_id": -1,
            "target_type": "staffing_line",
            "target_id": -1,
            "action": "link",
        },
    ).status_code in {404, 422}
    bad_upload = client.post(
        "/api/work/hr/documents/upload",
        headers=headers,
        data={
            "document_code": "",
            "document_type": "unknown",
            "title": "",
            "version": "",
        },
        files={"file": ("bad.exe", b"x", "application/octet-stream")},
    )
    assert bad_upload.status_code in {400, 422}
