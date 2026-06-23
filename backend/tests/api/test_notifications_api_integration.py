from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.notifications.service import create_notification
from app.models import Notification
from backend.tests.fixtures.app import demo_headers


def _create_test_notification(
    session: Session,
    *,
    recipient_id: int,
    sequence: int,
    dedupe_key: str | None = None,
) -> Notification:
    return create_notification(
        session,
        recipient_id=recipient_id,
        notification_type="test_event",
        title=f"Тестовое уведомление {sequence}",
        message=f"Сообщение {sequence}",
        target_section="profile",
        entity_type="employee_profile",
        entity_id=sequence,
        dedupe_key=dedupe_key or f"notification-api-test-{sequence}",
    )


def test_notifications_are_personal_deduplicated_and_marked_read(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    with client.app.state.database.session() as session:
        first = create_notification(
            session,
            recipient_id=int(employee_user["id"]),
            notification_type="test_event",
            title="Тестовое уведомление",
            message="Уведомление доступно только получателю.",
            target_section="profile",
            entity_type="employee_profile",
            entity_id=10,
            dedupe_key="notification-api-test",
        )
        duplicate = create_notification(
            session,
            recipient_id=int(employee_user["id"]),
            notification_type="test_event",
            title="Дубликат",
            message="Не должен создаваться.",
            target_section="profile",
            entity_type="employee_profile",
            entity_id=10,
            dedupe_key="notification-api-test",
        )
        session.flush()
        notification_id = first.id
        assert duplicate.id == first.id
        assert len(
            session.scalars(
                select(Notification).where(
                    Notification.dedupe_key
                    == f"notification-api-test:{employee_user['id']}"
                )
            ).all()
        ) == 1

    employee_headers = demo_headers(employee_user)
    hr_headers = demo_headers(hr_user)

    list_response = client.get("/api/notifications", headers=employee_headers)
    assert list_response.status_code == 200
    assert list_response.json()["unread_count"] == 1
    assert list_response.json()["items"][0]["id"] == notification_id
    assert list_response.json()["items"][0]["target_section"] == "profile"

    count_response = client.get(
        "/api/notifications/unread-count",
        headers=employee_headers,
    )
    assert count_response.status_code == 200
    assert count_response.json() == {"unread_count": 1}

    denied_response = client.post(
        f"/api/notifications/{notification_id}/read",
        headers=hr_headers,
    )
    assert denied_response.status_code == 404

    read_response = client.post(
        f"/api/notifications/{notification_id}/read",
        headers=employee_headers,
    )
    assert read_response.status_code == 200
    assert read_response.json()["read_at"] is not None

    read_all_response = client.post(
        "/api/notifications/read-all",
        headers=employee_headers,
    )
    assert read_all_response.status_code == 200
    assert read_all_response.json() == {"updated": 0}

    final_count = client.get(
        "/api/notifications/unread-count",
        headers=employee_headers,
    )
    assert final_count.json() == {"unread_count": 0}


def test_notification_endpoints_require_authentication(client: TestClient) -> None:
    responses = [
        client.get("/api/notifications"),
        client.get("/api/notifications/unread-count"),
        client.post("/api/notifications/read-all"),
        client.post("/api/notifications/1/read"),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401, 401]


def test_mark_all_reads_only_current_users_notifications(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    with client.app.state.database.session() as session:
        for sequence in range(3):
            _create_test_notification(
                session,
                recipient_id=int(employee_user["id"]),
                sequence=sequence,
            )
        _create_test_notification(
            session,
            recipient_id=int(hr_user["id"]),
            sequence=100,
        )

    read_all_response = client.post(
        "/api/notifications/read-all",
        headers=demo_headers(employee_user),
    )
    assert read_all_response.status_code == 200
    assert read_all_response.json() == {"updated": 3}

    employee_count = client.get(
        "/api/notifications/unread-count",
        headers=demo_headers(employee_user),
    )
    hr_count = client.get(
        "/api/notifications/unread-count",
        headers=demo_headers(hr_user),
    )
    assert employee_count.json() == {"unread_count": 0}
    assert hr_count.json() == {"unread_count": 1}


def test_notifications_are_ordered_newest_first_and_respect_limit(
    client: TestClient,
    employee_user: dict[str, Any],
) -> None:
    notification_ids: list[int] = []
    with client.app.state.database.session() as session:
        for sequence in range(4):
            notification = _create_test_notification(
                session,
                recipient_id=int(employee_user["id"]),
                sequence=sequence,
            )
            session.flush()
            notification_ids.append(notification.id)

    response = client.get(
        "/api/notifications",
        headers=demo_headers(employee_user),
        params={"limit": 2},
    )
    assert response.status_code == 200
    assert response.json()["unread_count"] == 4
    assert [item["id"] for item in response.json()["items"]] == list(
        reversed(notification_ids[-2:])
    )

    invalid_low = client.get(
        "/api/notifications",
        headers=demo_headers(employee_user),
        params={"limit": 0},
    )
    invalid_high = client.get(
        "/api/notifications",
        headers=demo_headers(employee_user),
        params={"limit": 101},
    )
    assert invalid_low.status_code == 422
    assert invalid_high.status_code == 422


def test_dedupe_key_is_scoped_to_recipient(
    client: TestClient,
    hr_user: dict[str, Any],
    employee_user: dict[str, Any],
) -> None:
    with client.app.state.database.session() as session:
        employee_notification = _create_test_notification(
            session,
            recipient_id=int(employee_user["id"]),
            sequence=1,
            dedupe_key="shared-event",
        )
        hr_notification = _create_test_notification(
            session,
            recipient_id=int(hr_user["id"]),
            sequence=1,
            dedupe_key="shared-event",
        )
        session.flush()

        assert employee_notification.id != hr_notification.id
        assert employee_notification.dedupe_key == f"shared-event:{employee_user['id']}"
        assert hr_notification.dedupe_key == f"shared-event:{hr_user['id']}"
