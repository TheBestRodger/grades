from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.tests.fixtures.api import (
    assignment_for_employee,
    create_launched_campaign_for_assignment,
    profile_for_campaign,
)
from backend.tests.fixtures.app import demo_headers
from backend.tests.fixtures.profile_answers import complete_profile_answers


def test_campaign_launch_with_selected_employee_only_and_credentials_export(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    tree_response = client.get("/api/organization/tree", headers=demo_headers(hr_user))
    assert tree_response.status_code == 200
    employee_assignment = assignment_for_employee(tree_response.json(), int(employee_user["id"]))

    launched = create_launched_campaign_for_assignment(
        client,
        hr_user=hr_user,
        assignment_id=int(employee_assignment["id"]),
    )
    assert launched["participants_expected"] == 1

    credentials_response = client.post(
        f"/api/hr/campaigns/{launched['id']}/waves/{launched['active_wave_id']}/credentials.xlsx",
        headers=demo_headers(hr_user),
    )
    assert credentials_response.status_code == 200
    assert credentials_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(credentials_response.content) > 100


def test_work_campaign_launches_with_selected_employee_without_selected_unit(
    client: TestClient,
    hr_user: dict[str, Any],
) -> None:
    headers = demo_headers(hr_user)
    tree_response = client.get("/api/work/organization/tree", headers=headers)
    assert tree_response.status_code == 200
    org_unit = next(node for node in _iter_nodes(tree_response.json()["nodes"]))

    line_response = client.post(
        f"/api/work/hr/org-units/{org_unit['id']}/staffing-lines",
        headers=headers,
        json={
            "title": f"Selected employee position {uuid4().hex[:8]}",
            "approved_fte": 1,
            "employees": [],
        },
    )
    assert line_response.status_code == 200

    employee_response = client.post(
        f"/api/work/hr/staffing-lines/{line_response.json()['staffing_line_id']}/employees/bulk",
        headers=headers,
        json={
            "employees": [
                {
                    "full_name": "Selected Employee",
                    "email": f"selected-{uuid4().hex[:8]}@profile.local",
                    "fte": 1,
                    "system_role": "employee",
                    "is_hr": False,
                }
            ]
        },
    )
    assert employee_response.status_code == 200
    assignment_id = int(employee_response.json()["added"][0]["assignment_id"])

    campaign_response = client.post(
        "/api/work/hr/campaigns",
        headers=headers,
        json={"name": f"Selected employee campaign {uuid4().hex[:8]}"},
    )
    assert campaign_response.status_code == 200
    campaign = campaign_response.json()
    wave_id = int(campaign["active_wave_id"])
    active_wave = next(wave for wave in campaign["waves"] if wave["id"] == wave_id)
    assert active_wave["can_launch"] is False

    empty_launch_response = client.post(
        f"/api/work/hr/campaigns/{campaign['id']}/waves/{wave_id}/launch",
        headers=headers,
    )
    assert empty_launch_response.status_code == 422

    include_response = client.put(
        f"/api/work/hr/campaigns/{campaign['id']}/waves/{wave_id}/assignments",
        headers=headers,
        json={"assignment_ids": [assignment_id], "action": "include"},
    )
    assert include_response.status_code == 200
    updated_campaign = include_response.json()
    updated_wave = next(wave for wave in updated_campaign["waves"] if wave["id"] == wave_id)
    assert updated_wave["participant_assignment_ids"] == [assignment_id]
    assert updated_wave["participants_expected"] == 1
    assert updated_wave["selected_org_unit_ids"] == []
    assert updated_wave["selected_units_count"] == 0
    assert updated_wave["can_launch"] is True

    launch_response = client.post(
        f"/api/work/hr/campaigns/{campaign['id']}/waves/{wave_id}/launch",
        headers=headers,
    )
    assert launch_response.status_code == 200
    launched_wave = next(wave for wave in launch_response.json()["waves"] if wave["id"] == wave_id)
    assert launched_wave["status"] == "active"
    assert launched_wave["participant_assignment_ids"] == [assignment_id]
    assert launched_wave["selected_org_unit_ids"] == []
    assert launched_wave["can_launch"] is False


def test_campaign_include_unit_create_wave_and_active_wave_edit_flow(
    client: TestClient,
    hr_user: dict[str, Any],
) -> None:
    headers = demo_headers(hr_user)
    tree_response = client.get("/api/organization/tree", headers=headers)
    assert tree_response.status_code == 200
    first_node = next(node for node in _iter_nodes(tree_response.json()["nodes"]))

    campaign_response = client.post(
        "/api/hr/campaigns",
        headers=headers,
        json={"name": f"Unit campaign {uuid4().hex[:8]}"},
    )
    assert campaign_response.status_code == 200
    campaign = campaign_response.json()

    wave_response = client.post(
        f"/api/hr/campaigns/{campaign['id']}/waves",
        headers=headers,
        json={"name": "Дополнительная волна"},
    )
    assert wave_response.status_code == 200
    wave_id = wave_response.json()["active_wave_id"]

    include_response = client.post(
        f"/api/hr/campaigns/{campaign['id']}/include-unit/{first_node['id']}",
        headers=headers,
        params={"wave_id": wave_id},
    )
    assert include_response.status_code == 200
    included_campaign = include_response.json()
    assert included_campaign["included_unit_name"] == first_node["name"]
    assert included_campaign["included_wave_id"] == wave_id
    assert included_campaign["new_participants"] > 0

    launch_response = client.post(
        f"/api/hr/campaigns/{campaign['id']}/waves/{wave_id}/launch",
        headers=headers,
    )
    assert launch_response.status_code == 200
    assert launch_response.json()["active_wave_id"] == wave_id

    edit_response = client.post(
        f"/api/hr/campaigns/{campaign['id']}/waves/{wave_id}/edit",
        headers=headers,
    )
    assert edit_response.status_code == 200
    assert any(wave["id"] == wave_id and wave["status"] == "editing" for wave in edit_response.json()["waves"])


def test_profile_submit_manager_verify_and_hr_accept_api_flow(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
    demo_users: list[dict[str, Any]],
) -> None:
    hr_headers = demo_headers(hr_user)
    employee_headers = demo_headers(employee_user)
    tree_response = client.get("/api/organization/tree", headers=hr_headers)
    assert tree_response.status_code == 200
    employee_assignment = assignment_for_employee(tree_response.json(), int(employee_user["id"]))

    campaign = create_launched_campaign_for_assignment(
        client,
        hr_user=hr_user,
        assignment_id=int(employee_assignment["id"]),
        name=f"Review flow {uuid4().hex[:8]}",
    )
    profile = profile_for_campaign(client, employee_user=employee_user, campaign_id=int(campaign["id"]))
    assigned_notifications = client.get(
        "/api/notifications",
        headers=employee_headers,
    )
    assert assigned_notifications.status_code == 200
    assert any(
        item["notification_type"] == "profile_assigned"
        for item in assigned_notifications.json()["items"]
    )

    draft_response = client.put(
        f"/api/my/profiles/{profile['id']}/draft",
        headers=employee_headers,
        json={"answers": {"position_purpose": "Поддерживает стабильный выпуск изменений."}},
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["workflow_status"] == "draft"

    submit_response = client.post(
        f"/api/my/profiles/{profile['id']}/submit",
        headers=employee_headers,
        json={
            "answers": complete_profile_answers(),
            "ai_without_ai_questions": list(complete_profile_answers()),
        },
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["workflow_status"] == "submitted"

    manager_headers = _manager_headers_with_profile(client, demo_users, int(profile["id"]))
    manager_notifications = client.get("/api/notifications", headers=manager_headers)
    assert manager_notifications.status_code == 200
    assert any(
        item["notification_type"] == "profile_submitted"
        and item["entity_id"] == str(profile["id"])
        for item in manager_notifications.json()["items"]
    )

    take_response = client.post(f"/api/manager/reviews/{profile['id']}/take", headers=manager_headers)
    assert take_response.status_code == 200
    assert take_response.json()["workflow_status"] == "under_review"

    manager_return_response = client.post(
        f"/api/manager/reviews/{profile['id']}/return",
        headers=manager_headers,
        json={"reason": "Нужно уточнить ожидаемый результат."},
    )
    assert manager_return_response.status_code == 200
    assert manager_return_response.json()["workflow_status"] == "returned_for_revision"
    employee_return_notifications = client.get(
        "/api/notifications",
        headers=employee_headers,
    )
    assert any(
        item["notification_type"] == "profile_returned"
        and item["entity_id"] == str(profile["id"])
        for item in employee_return_notifications.json()["items"]
    )

    resubmit_response = client.post(
        f"/api/my/profiles/{profile['id']}/submit",
        headers=employee_headers,
        json={
            "answers": complete_profile_answers(),
            "ai_without_ai_questions": list(complete_profile_answers()),
        },
    )
    assert resubmit_response.status_code == 200
    assert resubmit_response.json()["workflow_status"] == "submitted"

    retake_response = client.post(
        f"/api/manager/reviews/{profile['id']}/take",
        headers=manager_headers,
    )
    assert retake_response.status_code == 200

    verify_response = client.post(
        f"/api/manager/reviews/{profile['id']}/verify",
        headers=manager_headers,
        json={"comment": "Проверено руководителем."},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["workflow_status"] == "manager_verified"

    hr_queue_response = client.get("/api/hr/profile-reviews", headers=hr_headers)
    assert hr_queue_response.status_code == 200
    assert any(item["id"] == profile["id"] for item in hr_queue_response.json())

    hr_return_response = client.post(
        f"/api/hr/profile-reviews/{profile['id']}/return",
        headers=hr_headers,
        json={"reason": "Нужно повторное подтверждение руководителя."},
    )
    assert hr_return_response.status_code == 200
    assert hr_return_response.json()["workflow_status"] == "returned_by_hr"
    manager_returned_by_hr_notifications = client.get(
        "/api/notifications",
        headers=manager_headers,
    )
    assert any(
        item["notification_type"] == "profile_returned_by_hr"
        and item["entity_id"] == str(profile["id"])
        for item in manager_returned_by_hr_notifications.json()["items"]
    )

    reverify_response = client.post(
        f"/api/manager/reviews/{profile['id']}/verify",
        headers=manager_headers,
        json={"comment": "Повторно подтверждено руководителем."},
    )
    assert reverify_response.status_code == 200
    assert reverify_response.json()["workflow_status"] == "manager_verified"

    accept_response = client.post(
        f"/api/hr/profile-reviews/{profile['id']}/accept",
        headers=hr_headers,
        json={"comment": "Принято HR."},
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["workflow_status"] == "hr_accepted"
    accepted_notifications = client.get(
        "/api/notifications",
        headers=employee_headers,
    )
    assert accepted_notifications.status_code == 200
    assert any(
        item["notification_type"] == "profile_accepted"
        and item["entity_id"] == str(profile["id"])
        for item in accepted_notifications.json()["items"]
    )


def test_review_role_based_access_denies(
    client: TestClient,
    employee_user: dict[str, Any],
) -> None:
    response = client.get("/api/hr/profile-reviews", headers=demo_headers(employee_user))
    assert response.status_code == 403


def test_structure_add_update_and_force_delete_work_assignment(
    client: TestClient,
    hr_user: dict[str, Any],
) -> None:
    headers = demo_headers(hr_user)
    tree_response = client.get("/api/work/organization/tree", headers=headers)
    assert tree_response.status_code == 200
    org_unit = next(node for node in _iter_nodes(tree_response.json()["nodes"]))

    line_response = client.post(
        f"/api/work/hr/org-units/{org_unit['id']}/staffing-lines",
        headers=headers,
        json={"title": f"B10 position {uuid4().hex[:8]}", "approved_fte": 2, "employees": []},
    )
    assert line_response.status_code == 200
    line = line_response.json()

    add_response = client.post(
        f"/api/work/hr/staffing-lines/{line['staffing_line_id']}/employees/bulk",
        headers=headers,
        json={
            "employees": [
                {
                    "full_name": "B10 Employee",
                    "email": f"b10-{uuid4().hex[:8]}@profile.local",
                    "fte": 1,
                    "system_role": "employee",
                    "is_hr": False,
                }
            ]
        },
    )
    assert add_response.status_code == 200
    assignment_id = add_response.json()["added"][0]["assignment_id"]
    employee_id = add_response.json()["added"][0]["employee_id"]
    employee_notifications = client.get(
        "/api/notifications",
        headers={"X-Demo-User-Id": str(employee_id)},
    )
    assert employee_notifications.status_code == 200
    assert any(
        item["notification_type"] == "employee_added"
        for item in employee_notifications.json()["items"]
    )

    update_response = client.put(
        f"/api/work/hr/assignments/{assignment_id}/employee",
        headers=headers,
        json={
            "full_name": "B10 Employee Updated",
            "email": f"b10-updated-{uuid4().hex[:8]}@profile.local",
            "system_role": "manager",
            "is_hr": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["system_role"] == "manager"

    delete_response = client.delete(
        f"/api/work/hr/assignments/{assignment_id}",
        headers=headers,
        params={"force": True},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_assignments"] == 1


def _iter_nodes(nodes: list[dict[str, Any]]):
    for node in nodes:
        yield node
        yield from _iter_nodes(node.get("children", []))


def _manager_headers_with_profile(
    client: TestClient,
    users: list[dict[str, Any]],
    profile_id: int,
) -> dict[str, str]:
    for user in users:
        if user["role"] != "manager":
            continue
        headers = demo_headers(user)
        queue_response = client.get("/api/manager/reviews", headers=headers)
        assert queue_response.status_code == 200
        if any(item["id"] == profile_id for item in queue_response.json()):
            return headers
    raise AssertionError(f"No manager review queue contains profile {profile_id}.")
