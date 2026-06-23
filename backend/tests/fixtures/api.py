from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from .app import demo_headers


def iter_tree_nodes(nodes: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for node in nodes:
        yield node
        yield from iter_tree_nodes(node.get("children", []))


def first_staffing_line(tree: dict[str, Any]) -> dict[str, Any]:
    for node in iter_tree_nodes(tree.get("nodes", [])):
        for position in node.get("positions", []):
            return position
    raise AssertionError("Organization tree has no staffing lines.")


def assignment_for_employee(tree: dict[str, Any], employee_id: int) -> dict[str, Any]:
    for node in iter_tree_nodes(tree.get("nodes", [])):
        for position in node.get("positions", []):
            for assignment in position.get("assignments", []):
                if assignment["employee_id"] == employee_id:
                    return assignment
    raise AssertionError(f"Organization tree has no assignment for employee {employee_id}.")


def create_launched_campaign_for_assignment(
    client: TestClient,
    *,
    hr_user: dict[str, Any],
    assignment_id: int,
    name: str | None = None,
) -> dict[str, Any]:
    headers = demo_headers(hr_user)
    create_response = client.post(
        "/api/hr/campaigns",
        headers=headers,
        json={"name": name or f"API campaign {uuid4().hex[:8]}"},
    )
    assert create_response.status_code == 200
    campaign = create_response.json()
    wave_id = int(campaign["active_wave_id"])

    include_response = client.put(
        f"/api/hr/campaigns/{campaign['id']}/waves/{wave_id}/assignments",
        headers=headers,
        json={"assignment_ids": [assignment_id], "action": "include"},
    )
    assert include_response.status_code == 200

    launch_response = client.post(
        f"/api/hr/campaigns/{campaign['id']}/waves/{wave_id}/launch",
        headers=headers,
    )
    assert launch_response.status_code == 200
    launched = launch_response.json()
    assert launched["active_wave_id"] == wave_id
    assert assignment_id in launched["participant_assignment_ids"]
    return launched


def profile_for_campaign(
    client: TestClient,
    *,
    employee_user: dict[str, Any],
    campaign_id: int,
) -> dict[str, Any]:
    response = client.get("/api/my/profiles", headers=demo_headers(employee_user))
    assert response.status_code == 200
    return next(profile for profile in response.json() if profile["campaign_id"] == campaign_id)
