from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.infrastructure.ai.gateway import AiGatewayError, OffProvider
from app.models import Assignment, Document, DocumentLink, Employee
from backend.tests.fixtures.api import (
    assignment_for_employee,
    create_launched_campaign_for_assignment,
    first_staffing_line,
    profile_for_campaign,
)
from backend.tests.fixtures.app import demo_headers
from backend.tests.fixtures.profile_answers import complete_profile_answers

VALID_SUBMIT_PAYLOAD = {
    "answers": complete_profile_answers(),
    "ai_without_ai_questions": list(complete_profile_answers()),
}


class _FailingGateway:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def assess_profile_answer(self, payload: dict[str, object]) -> dict[str, object]:
        raise self.error


class _MalformedGateway:
    def assess_profile_answer(self, payload: dict[str, object]) -> dict[str, object]:
        return {"clarity_percent": "not-a-number", "status": "surprise"}


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
        json=VALID_SUBMIT_PAYLOAD,
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


def _verified_profile(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
    demo_users: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, str]]:
    profile = _make_profile(client, hr_user, employee_user)
    _submit_profile(client, employee_user, int(profile["id"]))
    manager_headers = _manager_headers_with_profile(
        client, demo_users, int(profile["id"])
    )
    take_response = client.post(
        f"/api/manager/reviews/{profile['id']}/take", headers=manager_headers
    )
    assert take_response.status_code == 200
    verify_response = client.post(
        f"/api/manager/reviews/{profile['id']}/verify",
        headers=manager_headers,
        json={"comment": "Проверено"},
    )
    assert verify_response.status_code == 200
    return profile, manager_headers


def _work_line(client: TestClient, hr_user: dict[str, Any]) -> dict[str, Any]:
    response = client.get("/api/work/organization/tree", headers=demo_headers(hr_user))
    assert response.status_code == 200
    return first_staffing_line(response.json())


def _upload_reviewed_document(
    client: TestClient, hr_user: dict[str, Any]
) -> dict[str, Any]:
    code = f"NEG-DOC-{uuid4().hex[:8]}"
    upload_response = client.post(
        "/api/work/hr/documents/upload",
        headers=demo_headers(hr_user),
        params={
            "filename": "negative-document.txt",
            "document_code": code,
            "document_type": "job_instruction",
            "title": "Negative path document",
            "version": "1.0",
        },
        content=b"Initial negative path source text.",
    )
    assert upload_response.status_code == 200
    document = _document_by_code(upload_response.json(), code)
    quality_response = client.put(
        f"/api/work/hr/documents/{document['id']}/quality",
        headers=demo_headers(hr_user),
        json={
            "ocr_quality_status": "good",
            "extracted_text": "Reviewed negative path text.",
        },
    )
    assert quality_response.status_code == 200
    return _document_by_code(quality_response.json(), code)


def _document_by_code(payload: dict[str, Any], document_code: str) -> dict[str, Any]:
    return next(
        item for item in payload["documents"] if item["document_code"] == document_code
    )


def _storage_snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize(
    "method,path,json_payload",
    [
        ("post", "/api/hr/campaigns", {"name": "Denied campaign"}),
        (
            "post",
            "/api/work/hr/org-units/1/staffing-lines",
            {"title": "Denied line", "approved_fte": 1, "employees": []},
        ),
        ("get", "/api/work/hr/documents", None),
        ("get", "/api/hr/settings/ai", None),
        ("put", "/api/hr/settings/ai", {"mode": "off", "provider": "off"}),
    ],
)
def test_employee_and_manager_without_hr_flag_are_denied_hr_sections(
    client: TestClient,
    employee_user: dict[str, Any],
    manager_user: dict[str, Any],
    method: str,
    path: str,
    json_payload: dict[str, Any] | None,
) -> None:
    for user in (employee_user, manager_user):
        response = getattr(client, method)(
            path, headers=demo_headers(user), json=json_payload
        )
        assert response.status_code == 403


def test_object_level_profile_read_write_submit_and_manager_queue_are_enforced(
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

    assert (
        client.get(
            f"/api/my/profiles/{profile['id']}/export.xlsx",
            headers=demo_headers(other_employee),
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/my/profiles/{profile['id']}/draft",
            headers=demo_headers(other_employee),
            json={"answers": {"position_purpose": "Чужой черновик"}},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/my/profiles/{profile['id']}/submit",
            headers=demo_headers(other_employee),
            json=VALID_SUBMIT_PAYLOAD,
        ).status_code
        == 404
    )

    _submit_profile(client, employee_user, int(profile["id"]))
    owning_manager = _manager_headers_with_profile(
        client, demo_users, int(profile["id"])
    )
    wrong_manager_user = next(
        user
        for user in demo_users
        if user["role"] == "manager" and demo_headers(user) != owning_manager
    )
    for action, payload in [
        ("take", None),
        ("verify", {"comment": "wrong manager"}),
        ("return", {"reason": "wrong manager cannot return"}),
    ]:
        response = client.post(
            f"/api/manager/reviews/{profile['id']}/{action}",
            headers=demo_headers(wrong_manager_user),
            json=payload,
        )
        assert response.status_code == 404


def test_document_registry_source_and_link_operations_share_hr_authorization(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
    manager_user: dict[str, Any],
) -> None:
    line = _work_line(client, hr_user)
    document = _upload_reviewed_document(client, hr_user)
    for user in (employee_user, manager_user):
        headers = demo_headers(user)
        assert client.get("/api/work/hr/documents", headers=headers).status_code == 403
        assert (
            client.get(
                f"/api/work/hr/documents/{document['id']}/source", headers=headers
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/work/hr/documents/link",
                headers=headers,
                json={
                    "staffing_line_id": line["id"],
                    "document_type": "job_instruction",
                    "document_id": document["id"],
                },
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/work/hr/documents/link",
                headers=headers,
                json={
                    "staffing_line_id": line["id"],
                    "document_type": "job_instruction",
                    "document_id": None,
                },
            ).status_code
            == 403
        )


def test_repeated_auth_notification_wave_and_document_link_commands_are_controlled(
    client: TestClient,
    test_app,
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
    assert client.post("/api/auth/logout", headers=auth_headers).status_code == 401
    assert (
        client.post("/api/auth/magic-link/consume", json={"token": token}).status_code
        == 409
    )

    tree = client.get("/api/organization/tree", headers=demo_headers(hr_user)).json()
    assignment = assignment_for_employee(tree, int(employee_user["id"]))
    campaign = create_launched_campaign_for_assignment(
        client, hr_user=hr_user, assignment_id=int(assignment["id"])
    )
    assert (
        client.post(
            f"/api/hr/campaigns/{campaign['id']}/waves/{campaign['active_wave_id']}/launch",
            headers=demo_headers(hr_user),
        ).status_code
        == 409
    )

    notification = client.get(
        "/api/notifications", headers=demo_headers(employee_user)
    ).json()["items"][0]
    assert (
        client.post(
            f"/api/notifications/{notification['id']}/read",
            headers=demo_headers(employee_user),
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/notifications/{notification['id']}/read",
            headers=demo_headers(employee_user),
        ).status_code
        == 200
    )

    line = _work_line(client, hr_user)
    document = _upload_reviewed_document(client, hr_user)
    link_payload = {
        "staffing_line_id": line["id"],
        "document_type": "job_instruction",
        "document_id": document["id"],
    }
    unlink_payload = {
        "staffing_line_id": line["id"],
        "document_type": "job_instruction",
        "document_id": None,
    }
    for payload in (link_payload, link_payload, unlink_payload, unlink_payload):
        assert (
            client.put(
                "/api/work/hr/documents/link",
                headers=demo_headers(hr_user),
                json=payload,
            ).status_code
            == 200
        )
    with test_app.state.database.session() as session:
        link_count = session.scalar(
            select(func.count())
            .select_from(DocumentLink)
            .where(DocumentLink.document_id == document["id"])
        )
    assert link_count == 1


def test_repeated_manager_and_hr_profile_decisions_are_conflicts_not_duplicates(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
    demo_users: list[dict[str, Any]],
) -> None:
    profile = _make_profile(client, hr_user, employee_user)
    _submit_profile(client, employee_user, int(profile["id"]))
    manager_headers = _manager_headers_with_profile(
        client, demo_users, int(profile["id"])
    )
    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/take", headers=manager_headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/take", headers=manager_headers
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/verify",
            headers=manager_headers,
            json={"comment": "ok"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/verify",
            headers=manager_headers,
            json={"comment": "again"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/manager/reviews/{profile['id']}/return",
            headers=manager_headers,
            json={"reason": "already processed"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/hr/profile-reviews/{profile['id']}/accept",
            headers=demo_headers(hr_user),
            json={"comment": "accepted"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/hr/profile-reviews/{profile['id']}/accept",
            headers=demo_headers(hr_user),
            json={"comment": "again"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/hr/profile-reviews/{profile['id']}/return",
            headers=demo_headers(hr_user),
            json={"reason": "already accepted"},
        ).status_code
        == 409
    )

    returned_profile, _ = _verified_profile(client, hr_user, employee_user, demo_users)
    assert (
        client.post(
            f"/api/hr/profile-reviews/{returned_profile['id']}/return",
            headers=demo_headers(hr_user),
            json={"reason": "needs manager follow-up"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/hr/profile-reviews/{returned_profile['id']}/return",
            headers=demo_headers(hr_user),
            json={"reason": "repeat return"},
        ).status_code
        == 409
    )


def test_forbidden_workflow_transitions_and_active_wave_mutation_are_rejected(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
    demo_users: list[dict[str, Any]],
) -> None:
    submitted_profile = _make_profile(client, hr_user, employee_user)
    _submit_profile(client, employee_user, int(submitted_profile["id"]))
    assert (
        client.post(
            f"/api/hr/profile-reviews/{submitted_profile['id']}/accept",
            headers=demo_headers(hr_user),
            json={"comment": "too early"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/hr/profile-reviews/{submitted_profile['id']}/return",
            headers=demo_headers(hr_user),
            json={"reason": "too early for HR"},
        ).status_code
        == 409
    )

    accepted_profile, _ = _verified_profile(client, hr_user, employee_user, demo_users)
    assert (
        client.post(
            f"/api/hr/profile-reviews/{accepted_profile['id']}/accept",
            headers=demo_headers(hr_user),
            json={"comment": "final"},
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/my/profiles/{accepted_profile['id']}/draft",
            headers=demo_headers(employee_user),
            json={"answers": {"position_purpose": "after final accept"}},
        ).status_code
        == 409
    )

    tree = client.get("/api/organization/tree", headers=demo_headers(hr_user)).json()
    assignment = assignment_for_employee(tree, int(employee_user["id"]))
    campaign = create_launched_campaign_for_assignment(
        client, hr_user=hr_user, assignment_id=int(assignment["id"])
    )
    assert (
        client.put(
            f"/api/hr/campaigns/{campaign['id']}/waves/{campaign['active_wave_id']}/assignments",
            headers=demo_headers(hr_user),
            json={"assignment_ids": [int(assignment["id"])], "action": "exclude"},
        ).status_code
        == 409
    )


def test_nonexistent_entities_return_not_found(
    client: TestClient, hr_user: dict[str, Any], manager_user: dict[str, Any]
) -> None:
    hr_headers = demo_headers(hr_user)
    manager_headers = demo_headers(manager_user)
    assert (
        client.post(
            "/api/hr/campaigns/999999/waves/999999/launch", headers=hr_headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/hr/profile-reviews/999999/accept",
            headers=hr_headers,
            json={"comment": "missing"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/manager/reviews/999999/take", headers=manager_headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/work/hr/documents/999999/source", headers=hr_headers
        ).status_code
        == 404
    )
    assert (
        client.delete("/api/work/hr/assignments/999999", headers=hr_headers).status_code
        == 404
    )


def test_bulk_employee_failure_after_partial_flush_rolls_back_rows(
    client: TestClient, test_app, hr_user: dict[str, Any]
) -> None:
    headers = demo_headers(hr_user)
    line = _work_line(client, hr_user)
    first_email = f"rollback-{uuid4().hex[:8]}@one.local"
    duplicate_username_email = first_email.replace("@one.local", "@two.local")
    response = client.post(
        f"/api/work/hr/staffing-lines/{line['id']}/employees/bulk",
        headers=headers,
        json={
            "employees": [
                {
                    "full_name": "Rollback One",
                    "email": first_email,
                    "fte": 1,
                    "system_role": "employee",
                    "is_hr": False,
                },
                {
                    "full_name": "Rollback Two",
                    "email": duplicate_username_email,
                    "fte": 1,
                    "system_role": "employee",
                    "is_hr": False,
                },
            ]
        },
    )
    assert response.status_code == 500
    with test_app.state.database.session() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Employee)
                .where(Employee.email.in_([first_email, duplicate_username_email]))
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(Assignment)
                .join(Employee)
                .where(Employee.email.in_([first_email, duplicate_username_email]))
            )
            == 0
        )


def test_document_upload_storage_write_failure_rolls_back_database_and_storage(
    client: TestClient, test_app, hr_user: dict[str, Any], monkeypatch
) -> None:
    from app.features.documents import upload as upload_module

    before = _storage_snapshot(Path(test_app.state.document_storage_dir))

    def fail_snapshot(*args, **kwargs):
        raise OSError("simulated snapshot write failure")

    monkeypatch.setattr(upload_module, "store_text_snapshot", fail_snapshot)
    code = f"ROLLBACK-{uuid4().hex[:8]}"
    response = client.post(
        "/api/work/hr/documents/upload",
        headers=demo_headers(hr_user),
        params={
            "filename": "rollback.txt",
            "document_code": code,
            "document_type": "job_instruction",
            "title": "Rollback document",
            "version": "v1",
        },
        content=b"document text",
    )
    assert response.status_code == 400
    assert "simulated" not in response.text
    with test_app.state.database.session() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Document)
                .where(Document.document_code == code)
            )
            == 0
        )
    assert _storage_snapshot(Path(test_app.state.document_storage_dir)) == before


def test_document_source_storage_read_error_is_controlled(
    client: TestClient, hr_user: dict[str, Any], monkeypatch
) -> None:
    document = _upload_reviewed_document(client, hr_user)

    def fail_read_bytes(self: Path) -> bytes:
        raise OSError("secret read failure traceback")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    response = client.get(
        f"/api/work/hr/documents/{document['id']}/source", headers=demo_headers(hr_user)
    )
    assert response.status_code == 404
    assert "secret read failure" not in response.text
    assert "traceback" not in response.text.lower()


def test_ai_failure_paths_are_sanitized_and_do_not_mutate_draft(
    client: TestClient, hr_user: dict[str, Any], employee_user: dict[str, Any]
) -> None:
    profile = _make_profile(client, hr_user, employee_user)
    assert (
        client.put(
            f"/api/my/profiles/{profile['id']}/draft",
            headers=demo_headers(employee_user),
            json={"answers": {"position_purpose": "Initial draft remains intact"}},
        ).status_code
        == 200
    )
    request = {
        "question_key": "position_purpose",
        "answers": {"position_purpose": "Check this answer"},
    }
    scenarios = [
        (_FailingGateway(TimeoutError("secret timeout traceback")), 503),
        (_MalformedGateway(), 502),
        (OffProvider(), 409),
    ]
    for gateway, expected in scenarios:
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
        assert "secret" not in response.text
        assert "traceback" not in response.text.lower()

    after = client.get("/api/my/profiles", headers=demo_headers(employee_user)).json()
    current = next(item for item in after if item["id"] == profile["id"])
    assert current["answers"]["position_purpose"] == "Initial draft remains intact"


@pytest.mark.parametrize(
    "path,payload,expected_status",
    [
        ("/api/hr/campaigns", {"name": ""}, 422),
        ("/api/hr/campaigns", {"name": "x" * 256}, 422),
        ("/api/hr/settings/ai", {"mode": "invalid", "provider": "off"}, 422),
        ("/api/hr/settings/ai", {"mode": "local", "provider": "off"}, 422),
    ],
)
def test_validation_matrix_for_required_strings_enums_lengths_and_field_combinations(
    client: TestClient,
    hr_user: dict[str, Any],
    path: str,
    payload: dict[str, Any],
    expected_status: int,
) -> None:
    method = "put" if "settings" in path else "post"
    assert (
        getattr(client, method)(
            path, headers=demo_headers(hr_user), json=payload
        ).status_code
        == expected_status
    )


def test_validation_matrix_for_negative_ids_duplicates_and_invalid_document_fields(
    client: TestClient, hr_user: dict[str, Any]
) -> None:
    headers = demo_headers(hr_user)
    assert (
        client.put(
            "/api/work/hr/documents/link",
            headers=headers,
            json={
                "staffing_line_id": -1,
                "document_type": "job_instruction",
                "document_id": -1,
            },
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/api/work/hr/documents/link",
            headers=headers,
            json={
                "staffing_line_id": 1,
                "document_type": "unknown",
                "document_id": None,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/hr/profile-reviews/bulk-return",
            headers=headers,
            json={"reason": "duplicate ids", "profile_ids": [1, 1]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/hr/profile-reviews/bulk-return",
            headers=headers,
            json={"reason": "bad selection", "profile_ids": [1], "org_unit_id": 1},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/work/hr/documents/upload",
            headers=headers,
            params={
                "filename": "bad.exe",
                "document_code": "",
                "document_type": "unknown",
                "title": "",
                "version": "",
            },
            content=b"x",
        ).status_code
        == 400
    )
