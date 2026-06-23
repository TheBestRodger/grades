from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.features.campaigns.schemas import CampaignAssignmentsUpdate, CampaignCreate, CampaignWaveCreate
from app.features.campaigns.rules import can_launch_wave
from app.features.documents.schemas import WorkDocumentLinkUpdate, WorkDocumentQualityUpdate
from app.features.hr_reviews.rules import can_hr_decide
from app.features.manager_reviews.rules import can_manager_decide, can_take_for_review
from app.features.settings.schemas import AiConfigurationUpdate, QuestionnaireQuestionSettingUpdate, QuestionnaireSettingsUpdate
from app.features.structure.credentials import archive_employee_email, login_from_email
from app.features.structure.deletion import active_wave_warning_message
from app.features.structure.rules import assigned_fte, has_enough_fte, remaining_fte, requested_fte
from app.infrastructure.files.document_storage import DocumentFileError, extract_initial_text, storage_token
from app.models import Employee


@dataclass(frozen=True)
class AssignmentLike:
    fte: float


@dataclass(frozen=True)
class StaffingLineLike:
    approved_fte: float
    assignments: list[AssignmentLike]


def test_structure_fte_rules_round_and_compare_with_tolerance() -> None:
    line = StaffingLineLike(approved_fte=1.0, assignments=[AssignmentLike(0.1), AssignmentLike(0.2)])

    assert assigned_fte(line) == 0.3
    assert remaining_fte(line) == 0.7
    assert requested_fte([AssignmentLike(0.33333), AssignmentLike(0.33333)]) == 0.6667
    assert has_enough_fte(line, 0.7)
    assert not has_enough_fte(line, 0.7001)


def test_wave_can_launch_when_editable_and_has_selected_participants() -> None:
    assert can_launch_wave("draft", 1)
    assert can_launch_wave("editing", 1)
    assert not can_launch_wave("draft", 0)
    assert not can_launch_wave("active", 1)


def test_active_wave_warning_message_limits_examples_and_reports_overflow() -> None:
    warnings = [
        {
            "employee_name": f"Сотрудник {index}",
            "staffing_title": "Инженер",
            "org_unit_name": "Отдел",
            "campaign_name": "Кампания",
            "wave_name": "Волна",
        }
        for index in range(6)
    ]

    message = active_wave_warning_message(warnings)

    assert "Сотрудник 0" in message
    assert "Сотрудник 4" in message
    assert "Сотрудник 5" not in message
    assert "Ещё затронуто: 1" in message


def test_document_file_helpers_extract_text_and_sanitize_storage_tokens() -> None:
    assert extract_initial_text("  текст  ".encode("utf-8-sig"), ".txt") == ("текст", "utf8_text")
    assert extract_initial_text(b"%PDF-1.4", ".pdf") == (None, "manual_ocr_required")
    assert storage_token(" ДИ / отдел №1 ") == "1"
    assert storage_token("...") == "document"

    with pytest.raises(DocumentFileError):
        extract_initial_text(b"\xff", ".txt")


def test_schema_validators_normalize_and_reject_invalid_payloads() -> None:
    assert CampaignCreate(name="  Кампания   профилирования ").name == "Кампания профилирования"
    assert CampaignWaveCreate(name="  Волна   1 ").name == "Волна 1"
    assert CampaignAssignmentsUpdate(assignment_ids=[1, 2], action="include").assignment_ids == [1, 2]

    with pytest.raises(ValidationError):
        CampaignAssignmentsUpdate(assignment_ids=[1, 1], action="include")
    with pytest.raises(ValidationError):
        WorkDocumentLinkUpdate(staffing_line_id=1, document_type="unknown", document_id=None)

    quality = WorkDocumentQualityUpdate(ocr_quality_status="good", extracted_text="  Проверенный текст  ")
    assert quality.extracted_text == "Проверенный текст"


def test_settings_schemas_enforce_provider_matrix_and_unique_question_keys() -> None:
    assert AiConfigurationUpdate(mode="off", provider="off").provider == "off"
    assert QuestionnaireQuestionSettingUpdate(question_key=" position_purpose ").question_key == "position_purpose"

    with pytest.raises(ValidationError):
        AiConfigurationUpdate(mode="off", provider="openai_compatible")
    with pytest.raises(ValidationError):
        AiConfigurationUpdate(mode="local", provider="openai_compatible")
    with pytest.raises(ValidationError):
        QuestionnaireSettingsUpdate(
            questions=[
                QuestionnaireQuestionSettingUpdate(question_key="position_purpose"),
                QuestionnaireQuestionSettingUpdate(question_key="position_purpose"),
            ]
        )


def test_review_transition_rules_are_explicit() -> None:
    assert can_take_for_review("submitted", has_revision=True)
    assert not can_take_for_review("submitted", has_revision=False)
    assert can_manager_decide("under_review", has_revision=True)
    assert can_manager_decide("returned_by_hr", has_revision=True)
    assert not can_manager_decide("draft", has_revision=True)
    assert can_hr_decide("manager_verified", has_revision=True)
    assert not can_hr_decide("manager_verified", has_revision=False)


def test_employee_login_and_archive_email_helpers_are_deterministic() -> None:
    employee = Employee(id=42, full_name="Test", email="  BAD Prefix@Example Domain.RU ", system_role="employee")

    assert login_from_email("  USER@Example.COM ") == "user@example.com"
    assert archive_employee_email(employee, datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)) == (
        "bad.prefix+deleted-42-1767225600000@example.domain.ru"
    )
