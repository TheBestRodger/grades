from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.features.campaigns.participants import set_participation, set_work_scope
from app.features.settings.service import ai_configuration_payload
from app.models import AiConfiguration, Assignment, Campaign, CampaignParticipant, CampaignWave, CampaignWaveUnitSelection, Employee


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, item: object) -> None:
        self.added.append(item)


def _settings(**overrides: object) -> Settings:
    data = {
        "app_name": "Test",
        "app_env": "test",
        "ai_mode": "off",
        "ai_provider": "off",
        "ai_base_url": None,
        "ai_model_name": None,
        "ai_api_token": None,
        "ai_request_timeout_seconds": 60,
        "database_url": "postgresql+psycopg://test:test@postgres:5432/test",
        "frontend_dist": Path("frontend/dist"),
        "work_staffing_file": None,
        "document_storage_dir": Path("documents"),
    }
    data.update(overrides)
    return Settings(**data)


def test_ai_configuration_payload_resolves_default_environment_without_exposing_secret() -> None:
    config = AiConfiguration(
        mode="default",
        provider="off",
        clarity_threshold=80,
        followup_strictness="strict",
    )
    settings = _settings(
        ai_mode="token",
        ai_provider="openai_compatible",
        ai_base_url="https://llm.example/v1",
        ai_model_name="gpt-test",
        ai_api_token="secret-token",
        ai_request_timeout_seconds=12,
    )

    public_payload = ai_configuration_payload(config, settings)
    secret_payload = ai_configuration_payload(config, settings, include_secret=True)

    assert public_payload["effective_mode"] == "token"
    assert public_payload["effective_provider"] == "openai_compatible"
    assert public_payload["available"] is True
    assert public_payload["api_token_configured"] is True
    assert public_payload["request_timeout_seconds"] == 12
    assert "api_token" not in public_payload
    assert secret_payload["api_token"] == "secret-token"


def test_ai_configuration_payload_requires_complete_local_or_token_settings() -> None:
    incomplete_token = AiConfiguration(
        mode="token",
        provider="openai_compatible",
        base_url="https://llm.example/v1",
        model_name="gpt-test",
        api_token=None,
        clarity_threshold=70,
        followup_strictness="balanced",
    )
    local = AiConfiguration(
        mode="local",
        provider="ollama",
        base_url="http://localhost:11434",
        model_name="llama3.1",
        clarity_threshold=70,
        followup_strictness="balanced",
    )

    assert ai_configuration_payload(incomplete_token, _settings())["available"] is False
    assert ai_configuration_payload(local, _settings())["available"] is True


def test_set_participation_includes_excludes_and_ignores_other_waves() -> None:
    session = RecordingSession()
    actor = Employee(id=10, full_name="HR", email="hr@example.com", system_role="hr")
    campaign = Campaign(id=1, name="Campaign", created_by_id=10, is_demo=True)
    wave = CampaignWave(id=2, campaign=campaign, name="Wave", created_by_id=10, is_demo=True)
    other_wave = CampaignWave(id=3, campaign=campaign, name="Other wave", created_by_id=10, is_demo=True)
    assignment = Assignment(id=100, employee_id=200, staffing_line_id=300, fte=1.0, is_demo=True)

    assert set_participation(session, actor, campaign, wave, [assignment], included=True) == 1
    created = session.added[-1]
    assert isinstance(created, CampaignParticipant)
    assert created.campaign is campaign
    assert created.wave is wave
    assert created.assignment_id == assignment.id
    assert created.expected_to_submit is True
    assert created.participation_status == "included"
    assert created.profile is not None

    existing = CampaignParticipant(
        campaign=campaign,
        wave=wave,
        campaign_wave_id=wave.id,
        assignment_id=101,
        expected_to_submit=True,
        participation_status="included",
        included_by_id=actor.id,
    )
    other_wave_participant = CampaignParticipant(
        campaign=campaign,
        wave=other_wave,
        campaign_wave_id=other_wave.id,
        assignment_id=102,
        expected_to_submit=True,
        participation_status="included",
        included_by_id=actor.id,
    )

    assert set_participation(
        session,
        actor,
        campaign,
        wave,
        [
            Assignment(id=101, employee_id=201, staffing_line_id=301, fte=1.0, is_demo=True),
            Assignment(id=102, employee_id=202, staffing_line_id=302, fte=1.0, is_demo=True),
        ],
        included=False,
    ) == 1
    assert existing.expected_to_submit is False
    assert existing.participation_status == "excluded"
    assert other_wave_participant.expected_to_submit is True


def test_set_work_scope_creates_and_updates_unit_selections() -> None:
    session = RecordingSession()
    actor = Employee(id=10, full_name="HR", email="hr@example.com", system_role="hr")
    wave = CampaignWave(id=2, campaign_id=1, name="Wave", created_by_id=10, is_demo=False)
    existing = CampaignWaveUnitSelection(
        wave=wave,
        org_unit_id=100,
        inclusion_status="included",
        selected_by_id=9,
        is_demo=False,
    )

    assert set_work_scope(session, actor, wave, {100, 101}, included=False) == 2
    created = session.added[-1]
    assert isinstance(created, CampaignWaveUnitSelection)
    assert existing.inclusion_status == "excluded"
    assert existing.selected_by_id == actor.id
    assert created.wave is wave
    assert created.org_unit_id == 101
    assert created.inclusion_status == "excluded"
