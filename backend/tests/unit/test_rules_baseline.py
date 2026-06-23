from __future__ import annotations

from dataclasses import dataclass

from app.features.campaigns.rules import (
    WAVE_STATUS_ACTIVE,
    WAVE_STATUS_DRAFT,
    WAVE_STATUS_EDITING,
    is_wave_editable,
    wave_status_label,
)
from app.features.organization.rules import (
    can_view_employee_only_scope,
    can_view_full_organization,
    effective_is_hr,
    has_hr_access,
)
from app.features.profiles.rules import (
    AI_ANSWER_STATUS_ACCEPTED,
    AI_ANSWER_STATUS_DRAFT,
    AI_ANSWER_STATUS_FILLED_WITHOUT_AI,
    AI_ANSWER_STATUS_IGNORED,
    AI_ANSWER_STATUS_REJECTED,
    is_ai_answer_accepted,
    is_ai_answer_rejected,
    normalize_ai_answer_status,
)


@dataclass(frozen=True)
class Actor:
    system_role: str
    is_hr: bool = False


def test_wave_status_rules_are_centralized() -> None:
    assert is_wave_editable(WAVE_STATUS_DRAFT)
    assert is_wave_editable(WAVE_STATUS_EDITING)
    assert not is_wave_editable(WAVE_STATUS_ACTIVE)
    assert wave_status_label(WAVE_STATUS_DRAFT) == "Черновик"
    assert wave_status_label("custom") == "custom"


def test_profile_ai_answer_status_rules_normalize_legacy_values() -> None:
    assert normalize_ai_answer_status(None) == AI_ANSWER_STATUS_DRAFT
    assert normalize_ai_answer_status("ignored") == AI_ANSWER_STATUS_IGNORED
    assert normalize_ai_answer_status("without_ai") == AI_ANSWER_STATUS_FILLED_WITHOUT_AI
    assert normalize_ai_answer_status(AI_ANSWER_STATUS_ACCEPTED) == AI_ANSWER_STATUS_ACCEPTED
    assert normalize_ai_answer_status(AI_ANSWER_STATUS_REJECTED) == AI_ANSWER_STATUS_REJECTED
    assert normalize_ai_answer_status("unknown") == AI_ANSWER_STATUS_DRAFT
    assert is_ai_answer_accepted(AI_ANSWER_STATUS_ACCEPTED)
    assert is_ai_answer_rejected(AI_ANSWER_STATUS_REJECTED)


def test_role_rules_keep_hr_as_additive_permission() -> None:
    employee = Actor("employee")
    manager_hr = Actor("manager", is_hr=True)
    legacy_hr = Actor("hr")

    assert not has_hr_access(employee)
    assert can_view_employee_only_scope(employee)
    assert has_hr_access(manager_hr)
    assert can_view_full_organization(manager_hr)
    assert has_hr_access(legacy_hr)
    assert effective_is_hr("manager", True) is True
    assert effective_is_hr("manager", False) is False
