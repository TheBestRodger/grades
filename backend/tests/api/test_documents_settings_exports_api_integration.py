from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.tests.fixtures.api import first_staffing_line, iter_tree_nodes
from backend.tests.fixtures.app import demo_headers


def test_work_document_upload_quality_link_unlink_and_source_download(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    headers = demo_headers(hr_user)
    work_tree_response = client.get("/api/work/organization/tree", headers=headers)
    assert work_tree_response.status_code == 200
    line = first_staffing_line(work_tree_response.json())

    document_code = f"B10-DOC-{uuid4().hex[:8]}"
    upload_response = client.post(
        "/api/work/hr/documents/upload",
        headers=headers,
        params={
            "filename": "b10-document.txt",
            "document_code": document_code,
            "document_type": "job_instruction",
            "title": "B10 job instruction",
            "version": "1.0",
        },
        content=b"Initial source text for integration test.",
    )
    assert upload_response.status_code == 200
    document = _document_by_code(upload_response.json(), document_code)
    assert document["ocr_quality_status"] in {"pending", "requires_text"}
    assert document["has_stored_original"] is True

    quality_response = client.put(
        f"/api/work/hr/documents/{document['id']}/quality",
        headers=headers,
        json={
            "ocr_quality_status": "good",
            "extracted_text": "Verified document text for integration test.",
        },
    )
    assert quality_response.status_code == 200
    reviewed = _document_by_code(quality_response.json(), document_code)
    assert reviewed["ocr_quality_status"] == "good"

    link_response = client.put(
        "/api/work/hr/documents/link",
        headers=headers,
        json={
            "staffing_line_id": line["id"],
            "document_type": "job_instruction",
            "document_id": document["id"],
        },
    )
    assert link_response.status_code == 200
    linked = _document_by_code(link_response.json(), document_code)
    assert linked["links"][0]["target_id"] == line["id"]
    assert linked["links"][0]["link_status"] == "confirmed"

    source_response = client.get(f"/api/work/hr/documents/{document['id']}/source", headers=headers)
    assert source_response.status_code == 200
    assert source_response.content == b"Initial source text for integration test."

    unlink_response = client.put(
        "/api/work/hr/documents/link",
        headers=headers,
        json={
            "staffing_line_id": line["id"],
            "document_type": "job_instruction",
            "document_id": None,
        },
    )
    assert unlink_response.status_code == 200
    unlinked = _document_by_code(unlink_response.json(), document_code)
    assert len(unlinked["links"]) == 1
    assert unlinked["links"][0]["target_id"] == line["id"]
    assert unlinked["links"][0]["link_status"] == "removed"

    denied_response = client.get("/api/work/hr/documents", headers=demo_headers(employee_user))
    assert denied_response.status_code == 403


def test_settings_get_update_and_exports_csv_smoke(
    client: TestClient,
    hr_user: dict[str, Any],
) -> None:
    headers = demo_headers(hr_user)

    ai_get = client.get("/api/hr/settings/ai", headers=headers)
    assert ai_get.status_code == 200
    assert ai_get.json()["mode"] in {"off", "default", "local", "token"}

    ai_update = client.put(
        "/api/hr/settings/ai",
        headers=headers,
        json={
            "mode": "off",
            "provider": "off",
            "clarity_threshold": 65,
            "followup_strictness": "soft",
        },
    )
    assert ai_update.status_code == 200
    assert ai_update.json()["clarity_threshold"] == 65

    questionnaire_get = client.get("/api/hr/settings/questionnaire", headers=headers)
    assert questionnaire_get.status_code == 200
    first_question = questionnaire_get.json()["questions"][0]

    questionnaire_update = client.put(
        "/api/hr/settings/questionnaire",
        headers=headers,
        json={
            "questions": [
                {
                    "question_key": first_question["question_key"],
                    "ai_check_enabled": False,
                    "good_example": "Достаточно конкретный пример.",
                    "bad_example": "Слишком общий ответ.",
                    "requirements": "Ответ должен описывать результат.",
                }
            ]
        },
    )
    assert questionnaire_update.status_code == 200
    changed_question = questionnaire_update.json()["questions"][0]
    assert changed_question["question_key"] == first_question["question_key"]
    assert changed_question["ai_check_enabled"] is False

    profiles_csv = client.get("/api/hr/exports/profiles.csv", headers=headers)
    assert profiles_csv.status_code == 200
    assert profiles_csv.headers["content-type"].startswith("text/csv")
    assert "campaign_name" in profiles_csv.text

    campaigns_csv = client.get("/api/hr/exports/campaigns.csv", headers=headers)
    assert campaigns_csv.status_code == 200
    assert campaigns_csv.headers["content-type"].startswith("text/csv")
    assert "campaign_name" in campaigns_csv.text


def test_work_document_events_notify_global_hr_user(
    client: TestClient,
    hr_user: dict[str, Any],
) -> None:
    main_hr_headers = demo_headers(hr_user)
    work_tree_response = client.get(
        "/api/work/organization/tree",
        headers=main_hr_headers,
    )
    assert work_tree_response.status_code == 200
    org_unit = next(iter(iter_tree_nodes(work_tree_response.json()["nodes"])))

    line_response = client.post(
        f"/api/work/hr/org-units/{org_unit['id']}/staffing-lines",
        headers=main_hr_headers,
        json={
            "title": f"Notification position {uuid4().hex[:8]}",
            "approved_fte": 1,
            "employees": [],
        },
    )
    assert line_response.status_code == 200
    staffing_line_id = int(line_response.json()["staffing_line_id"])

    recipient_response = client.post(
        f"/api/work/hr/staffing-lines/{staffing_line_id}/employees/bulk",
        headers=main_hr_headers,
        json={
            "employees": [
                {
                    "full_name": "Notification Work HR",
                    "email": f"notification-hr-{uuid4().hex[:8]}@profile.local",
                    "fte": 1,
                    "system_role": "manager",
                    "is_hr": True,
                }
            ]
        },
    )
    assert recipient_response.status_code == 200
    work_hr = recipient_response.json()["added"][0]
    work_hr_headers = {"X-Demo-User-Id": str(work_hr["employee_id"])}

    document_code = f"NOTIFY-DOC-{uuid4().hex[:8]}"
    upload_response = client.post(
        "/api/work/hr/documents/upload",
        headers=work_hr_headers,
        params={
            "filename": "notification-document.txt",
            "document_code": document_code,
            "document_type": "job_instruction",
            "title": "Notification document",
            "version": "1.0",
        },
        content=b"Notification document source.",
    )
    assert upload_response.status_code == 200
    document = _document_by_code(upload_response.json(), document_code)

    uploaded_notifications = client.get(
        "/api/notifications",
        headers=main_hr_headers,
    )
    assert uploaded_notifications.status_code == 200
    assert any(
        item["notification_type"] == "document_uploaded"
        and item["entity_id"] == str(document["id"])
        for item in uploaded_notifications.json()["items"]
    )

    quality_response = client.put(
        f"/api/work/hr/documents/{document['id']}/quality",
        headers=work_hr_headers,
        json={
            "ocr_quality_status": "good",
            "extracted_text": "Verified notification document text.",
        },
    )
    assert quality_response.status_code == 200

    link_response = client.put(
        "/api/work/hr/documents/link",
        headers=work_hr_headers,
        json={
            "staffing_line_id": staffing_line_id,
            "document_type": "job_instruction",
            "document_id": document["id"],
        },
    )
    assert link_response.status_code == 200

    linked_notifications = client.get(
        "/api/notifications",
        headers=main_hr_headers,
    )
    assert linked_notifications.status_code == 200
    assert any(
        item["notification_type"] == "document_linked"
        and item["entity_id"] == str(staffing_line_id)
        for item in linked_notifications.json()["items"]
    )


def _document_by_code(payload: dict[str, Any], document_code: str) -> dict[str, Any]:
    for document in payload["documents"]:
        if document["document_code"] == document_code:
            return document
    raise AssertionError(f"Document {document_code} not found in registry response.")
