from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.features.campaigns.errors import CampaignOperationError
from app.features.campaigns.participants import set_campaign_assignments
from app.features.campaigns.schemas import CampaignAssignmentsUpdate
from app.features.campaigns.waves import edit_campaign_wave, launch_campaign_wave
from app.features.hr_reviews.schemas import ReviewReturnRequest
from app.features.hr_reviews.service import get_hr_review_queue, return_to_manager
from app.features.profiles.ai_answers import assess_profile_answer
from app.features.profiles.routing import route_current, route_reason
from app.features.profiles.schemas import AiProfileAnswerCheckRequest, ProfileAnswersRequest
from app.features.profiles.submit import submit_profile
from app.models import (
    Assignment,
    Campaign,
    CampaignParticipant,
    CampaignWave,
    Employee,
    EmployeeProfile,
    OrgUnit,
    StaffingLine,
)
from backend.tests.fixtures.profile_answers import complete_profile_answers
from backend.tests.fixtures.app import demo_headers


def test_submit_resolves_nearest_manager_up_the_unit_tree(client: TestClient) -> None:
    app = client.app
    with app.state.database.session() as session:
        fixture = _profile_fixture(session, manager_level="department")

        submitted = submit_profile(
            session,
            fixture.employee,
            fixture.profile.id,
            ProfileAnswersRequest(answers=complete_profile_answers()),
            "off",
        )

        session.refresh(fixture.employee_assignment)
        assert fixture.employee_assignment.manager_assignment_id == fixture.department_manager_assignment.id
        assert submitted["workflow_status"] == "submitted"
        assert submitted["route_path"] == ["Сотрудник", "Руководитель", "HR"]
        assert fixture.department_manager.full_name in submitted["route_current"]


def test_submit_climbs_to_parent_unit_manager_when_direct_unit_has_none(client: TestClient) -> None:
    app = client.app
    with app.state.database.session() as session:
        fixture = _profile_fixture(session, manager_level="parent")

        submit_profile(
            session,
            fixture.employee,
            fixture.profile.id,
            ProfileAnswersRequest(answers=complete_profile_answers()),
            "off",
        )

        session.refresh(fixture.employee_assignment)
        assert fixture.employee_assignment.manager_assignment_id == fixture.parent_manager_assignment.id
        assert route_current(fixture.profile).startswith("Руководитель:")
        assert "Анкета находится у непосредственного руководителя." == route_reason(fixture.profile)


def test_submit_without_any_manager_goes_directly_to_hr_queue(client: TestClient) -> None:
    app = client.app
    with app.state.database.session() as session:
        fixture = _profile_fixture(session, manager_level="none")

        submitted = submit_profile(
            session,
            fixture.employee,
            fixture.profile.id,
            ProfileAnswersRequest(answers=complete_profile_answers()),
            "off",
        )
        hr_queue_ids = {
            item["id"]
            for item in get_hr_review_queue(session, is_demo=True)
        }

        session.refresh(fixture.employee_assignment)
        assert fixture.employee_assignment.manager_assignment_id is None
        assert submitted["workflow_status"] == "manager_verified"
        assert submitted["route_path"] == ["Сотрудник", "HR"]
        assert submitted["route_current"] == "HR"
        assert "сразу в HR" in route_reason(fixture.profile)
        assert fixture.profile.id in hr_queue_ids


def test_hr_return_restores_editing_for_manager_profile_sent_directly_to_hr(
    client: TestClient,
) -> None:
    with client.app.state.database.session() as session:
        fixture = _profile_fixture(
            session,
            manager_level="none",
            employee_role="manager",
        )
        submitted = submit_profile(
            session,
            fixture.employee,
            fixture.profile.id,
            ProfileAnswersRequest(answers=complete_profile_answers()),
            "off",
        )
        returned = return_to_manager(
            session,
            fixture.hr,
            fixture.profile.id,
            ReviewReturnRequest(reason="Уточните управленческий результат."),
        )
        employee_id = fixture.employee.id
        profile_id = fixture.profile.id

        assert submitted["workflow_status"] == "manager_verified"
        assert returned["workflow_status"] == "returned_for_revision"

    headers = demo_headers({"id": employee_id})
    profiles_response = client.get("/api/my/profiles", headers=headers)
    assert profiles_response.status_code == 200
    profile = next(item for item in profiles_response.json() if item["id"] == profile_id)
    assert profile["workflow_status"] == "returned_for_revision"
    assert profile["can_edit"] is True
    assert profile["route_current"] == "Сотрудник"
    assert profile["review_events"][0]["action"] == "hr_returned"
    assert profile["review_events"][0]["comment"] == "Уточните управленческий результат."

    draft_response = client.put(
        f"/api/my/profiles/{profile_id}/draft",
        headers=headers,
        json={"answers": complete_profile_answers()},
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["workflow_status"] == "draft"

    notifications_response = client.get("/api/notifications", headers=headers)
    assert notifications_response.status_code == 200
    assert any(
        item["notification_type"] == "profile_returned_by_hr"
        and item["entity_id"] == str(profile_id)
        and item["target_section"] == "profile"
        for item in notifications_response.json()["items"]
    )


def test_submit_persists_ai_answer_statuses_without_rechecking_accepted_answers(client: TestClient) -> None:
    app = client.app
    with app.state.database.session() as session:
        fixture = _profile_fixture(session, manager_level="department")
        request = ProfileAnswersRequest(
            answers=complete_profile_answers(),
            ai_checked_questions=["position_purpose", "complex_task_example"],
            ai_ignored_questions=["complex_task_example"],
            ai_without_ai_questions=["comments"],
            ai_answer_statuses={
                "position_purpose": "accepted",
                "complex_task_example": "rejected",
            },
        )

        submitted = submit_profile(session, fixture.employee, fixture.profile.id, request, "token")
        revision = fixture.profile.revisions[0]
        assisted = json.loads(revision.assisted_sections_json)

        assert submitted["revisions"][0]["assistance_level"] == "mixed"
        assert revision.assistant_mode == "ai_checked"
        assert assisted["answer_statuses"]["position_purpose"] == "accepted"
        assert assisted["answer_statuses"]["complex_task_example"] == "ignored_ai"
        assert assisted["answer_statuses"]["comments"] == "filled_without_ai"


def test_ai_answer_check_accepts_clear_answer_and_suppresses_followup(client: TestClient) -> None:
    app = client.app
    with app.state.database.session() as session:
        fixture = _profile_fixture(session, manager_level="department")
        request = AiProfileAnswerCheckRequest(
            question_key="position_purpose",
            answers={"position_purpose": "Обеспечивает стабильный выпуск релизов без критичных дефектов."},
        )

        result = assess_profile_answer(
            session,
            fixture.employee,
            fixture.profile.id,
            request,
            _FakeGateway(clarity_percent=92, status="accepted", followup_question="Лишний вопрос?"),
            clarity_threshold=70,
            followup_strictness="balanced",
        )

        assert result["accepted"] is True
        assert result["followup_question"] == ""
        assert result["payload_policy"] == "anonymized_no_personal_data"


def test_campaign_active_wave_cannot_change_until_editing_mode(client: TestClient) -> None:
    app = client.app
    with app.state.database.session() as session:
        fixture = _profile_fixture(session, manager_level="department")
        launch_campaign_wave(session, fixture.hr, fixture.campaign.id, fixture.wave.id, is_demo=True)

        try:
            set_campaign_assignments(
                session,
                fixture.hr,
                fixture.campaign.id,
                fixture.wave.id,
                CampaignAssignmentsUpdate(
                    assignment_ids=[fixture.employee_assignment.id],
                    action="exclude",
                ),
                is_demo=True,
            )
        except CampaignOperationError as exc:
            assert exc.status_code == 409
            assert "сначала возьмите волну в редакцию" in exc.message
        else:
            raise AssertionError("Active wave participant change must be blocked")

        edit_campaign_wave(session, fixture.hr, fixture.campaign.id, fixture.wave.id, is_demo=True)
        changed = set_campaign_assignments(
            session,
            fixture.hr,
            fixture.campaign.id,
            fixture.wave.id,
            CampaignAssignmentsUpdate(
                assignment_ids=[fixture.employee_assignment.id],
                action="exclude",
            ),
            is_demo=True,
        )
        assert changed["participant_action"] == "exclude"
        assert changed["changed_participants"] == 1


class _FakeGateway:
    def __init__(
        self,
        *,
        clarity_percent: int,
        status: str,
        followup_question: str,
    ) -> None:
        self.clarity_percent = clarity_percent
        self.status = status
        self.followup_question = followup_question

    def assess_profile_answer(self, payload: dict[str, object]) -> dict[str, object]:
        assert payload["question_key"] == "position_purpose"
        assert "@" not in str(payload)
        return {
            "available": True,
            "provider": "fake",
            "model": "fake-model",
            "clarity_percent": self.clarity_percent,
            "status": self.status,
            "explanation": "Ответ достаточно конкретный.",
            "followup_question": self.followup_question,
            "raw_text": "fake",
        }


class _Fixture:
    def __init__(
        self,
        *,
        hr: Employee,
        employee: Employee,
        department_manager: Employee,
        parent_manager: Employee,
        employee_assignment: Assignment,
        department_manager_assignment: Assignment,
        parent_manager_assignment: Assignment,
        campaign: Campaign,
        wave: CampaignWave,
        profile: EmployeeProfile,
    ) -> None:
        self.hr = hr
        self.employee = employee
        self.department_manager = department_manager
        self.parent_manager = parent_manager
        self.employee_assignment = employee_assignment
        self.department_manager_assignment = department_manager_assignment
        self.parent_manager_assignment = parent_manager_assignment
        self.campaign = campaign
        self.wave = wave
        self.profile = profile


def _profile_fixture(
    session,
    *,
    manager_level: str,
    employee_role: str = "employee",
) -> _Fixture:
    suffix = uuid4().hex[:8]
    root = OrgUnit(name=f"Root {suffix}", path=f"TEST-{suffix}", is_demo=True)
    parent = OrgUnit(name=f"Parent {suffix}", path=f"TEST-{suffix}/Parent", parent=root, is_demo=True)
    department = OrgUnit(
        name=f"Department {suffix}",
        path=f"TEST-{suffix}/Parent/Department",
        parent=parent,
        is_demo=True,
    )
    child = OrgUnit(
        name=f"Child {suffix}",
        path=f"TEST-{suffix}/Parent/Department/Child",
        parent=department,
        is_demo=True,
    )
    session.add_all([root, parent, department, child])
    session.flush()

    hr = _employee(f"hr-{suffix}@profile.local", "HR Local", "hr")
    employee = _employee(
        f"employee-{suffix}@profile.local",
        "Employee Local",
        employee_role,
    )
    department_manager = _employee(
        f"department-manager-{suffix}@profile.local",
        "Department Manager",
        "manager",
    )
    parent_manager = _employee(f"parent-manager-{suffix}@profile.local", "Parent Manager", "manager")
    session.add_all([hr, employee, department_manager, parent_manager])
    session.flush()

    employee_line = StaffingLine(org_unit=child, title=f"Специалист {suffix}", approved_fte=1, is_demo=True)
    department_manager_line = StaffingLine(
        org_unit=department,
        title=f"Начальник отдела {suffix}",
        approved_fte=1,
        is_demo=True,
    )
    parent_manager_line = StaffingLine(
        org_unit=parent,
        title=f"Руководитель направления {suffix}",
        approved_fte=1,
        is_demo=True,
    )
    session.add_all([employee_line, department_manager_line, parent_manager_line])
    session.flush()

    employee_assignment = Assignment(employee=employee, staffing_line=employee_line, fte=1, is_demo=True)
    department_manager_assignment = Assignment(
        employee=department_manager,
        staffing_line=department_manager_line,
        fte=1,
        is_demo=True,
    )
    parent_manager_assignment = Assignment(
        employee=parent_manager,
        staffing_line=parent_manager_line,
        fte=1,
        is_demo=True,
    )
    session.add_all([employee_assignment, department_manager_assignment, parent_manager_assignment])
    session.flush()
    if manager_level == "department":
        employee_assignment.manager_assignment_id = department_manager_assignment.id
    elif manager_level == "parent":
        session.delete(department_manager_assignment)
    elif manager_level == "none":
        session.delete(department_manager_assignment)
        session.delete(parent_manager_assignment)
    session.flush()

    campaign = Campaign(name=f"Critical campaign {suffix}", status="active", created_by_id=hr.id, is_demo=True)
    wave = CampaignWave(campaign=campaign, name="Волна 1", status="draft", created_by_id=hr.id, is_demo=True)
    participant = CampaignParticipant(
        campaign=campaign,
        wave=wave,
        assignment=employee_assignment,
        participation_status="included",
        expected_to_submit=True,
        included_by_id=hr.id,
    )
    profile = EmployeeProfile(participant=participant)
    session.add_all([campaign, wave, participant, profile])
    session.flush()
    return _Fixture(
        hr=hr,
        employee=employee,
        department_manager=department_manager,
        parent_manager=parent_manager,
        employee_assignment=employee_assignment,
        department_manager_assignment=department_manager_assignment,
        parent_manager_assignment=parent_manager_assignment,
        campaign=campaign,
        wave=wave,
        profile=profile,
    )


def _employee(email: str, full_name: str, role: str) -> Employee:
    return Employee(
        full_name=full_name,
        email=email,
        username=email,
        system_role=role,
        is_hr=role == "hr",
        is_demo=True,
    )
