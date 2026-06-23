from __future__ import annotations

from pathlib import Path
import json

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.features.auth.service import (
    actor_from_authorization,
    consume_magic_link,
    logout_session,
    request_magic_link,
)
from app.features.campaigns.errors import CampaignOperationError
from app.features.campaigns.service import create_campaign, include_unit_in_campaign, launch_campaign_wave
from app.features.campaigns.schemas import CampaignCreate
from app.features.imports.grades_documents import (
    DOCUMENTS_DIR,
    _default_staffing_file,
    import_grades_documents,
)
from app.features.profiles.draft import save_draft
from app.features.profiles.schemas import ProfileAnswersRequest
from app.features.profiles.service import get_my_profiles
from app.features.profiles.submit import submit_profile
from app.main import create_app
from app.models import Document, DocumentLink, Employee, OrgUnit
from app.runtime_setup import prepare_runtime_database


def app_for_test(tmp_path: Path):
    settings = Settings(
        app_name="Test app",
        app_env="test",
        ai_mode="off",
        ai_provider="off",
        ai_base_url=None,
        ai_model_name=None,
        ai_api_token=None,
        ai_request_timeout_seconds=60,
        database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}",
        frontend_dist=tmp_path / "missing-dist",
        work_staffing_file=None,
        document_storage_dir=tmp_path / "document_storage",
    )
    prepare_runtime_database(settings)
    return create_app(settings)


def test_auth_service_magic_link_session_lifecycle(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    with TestClient(app):
        with app.state.database.session() as session:
            requested = request_magic_link(session, "HR@profile.local", app.state.settings)
            assert requested["delivery_mode"] == "local_link"
            assert requested["login_token"]
            session.flush()

            consumed = consume_magic_link(session, str(requested["login_token"]))
            token = str(consumed["token"])
            assert consumed["user"]["email"] == "hr@profile.local"
            session.flush()

            actor = actor_from_authorization(session, f"Bearer {token}")
            assert actor is not None
            assert actor.email == "hr@profile.local"

            logged_out = logout_session(session, f"Bearer {token}")
            assert logged_out == {"revoked": True}


def test_profile_service_saves_draft_and_submit_creates_revision(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    with TestClient(app):
        with app.state.database.session() as session:
            hr = _employee(session, "hr@profile.local")
            employee = _employee(session, "specialist@profile.local")
            department = _unit(session, "Отдел сопровождения процессов")

            campaign = create_campaign(
                session,
                hr,
                CampaignCreate(name="Service profile baseline"),
                is_demo=True,
            )
            include_unit_in_campaign(session, hr, int(campaign["id"]), department.id, is_demo=True)
            profile = next(
                item for item in get_my_profiles(session, employee) if item["campaign_id"] == campaign["id"]
            )

            draft = save_draft(
                session,
                employee,
                int(profile["id"]),
                ProfileAnswersRequest(answers={"position_purpose": "Проверяю качество релиза."}),
                "off",
            )
            assert draft["workflow_status"] == "draft"
            assert draft["answers"]["position_purpose"] == "Проверяю качество релиза."

            submitted = submit_profile(
                session,
                employee,
                int(profile["id"]),
                ProfileAnswersRequest(answers=_complete_answers()),
                "off",
            )
            assert submitted["workflow_status"] == "submitted"
            assert submitted["revisions"][0]["revision_no"] == 1


def test_campaign_service_rejects_empty_wave_launch(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    with TestClient(app):
        with app.state.database.session() as session:
            hr = _employee(session, "hr@profile.local")
            campaign = create_campaign(
                session,
                hr,
                CampaignCreate(name="Empty wave baseline"),
                is_demo=True,
            )

            try:
                launch_campaign_wave(session, hr, int(campaign["id"]), int(campaign["active_wave_id"]))
            except CampaignOperationError as exc:
                assert exc.status_code == 422
                assert "минимум одного участника" in exc.message
            else:
                raise AssertionError("Empty campaign wave launch must fail")


def test_grades_document_import_is_idempotent(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)
    staffing_file = _default_staffing_file()
    assert staffing_file.exists()
    assert DOCUMENTS_DIR.exists()

    with TestClient(app):
        with app.state.database.session() as session:
            import_grades_documents(
                session,
                staffing_file=staffing_file,
                documents_dir=DOCUMENTS_DIR,
                storage_dir=tmp_path / "document_storage",
                apply_changes=True,
            )
            first_counts = _document_counts(session)

            report = import_grades_documents(
                session,
                staffing_file=staffing_file,
                documents_dir=DOCUMENTS_DIR,
                storage_dir=tmp_path / "document_storage",
                apply_changes=True,
            )
            second_counts = _document_counts(session)

            assert second_counts == first_counts
            assert report.documents_created == 0
            assert report.links_created == 0


def _employee(session, email: str) -> Employee:
    employee = session.scalar(select(Employee).where(Employee.email == email, Employee.is_demo.is_(True)))
    assert employee is not None
    return employee


def _unit(session, name: str) -> OrgUnit:
    unit = session.scalar(select(OrgUnit).where(OrgUnit.name == name, OrgUnit.is_demo.is_(True)))
    assert unit is not None
    return unit


def _document_counts(session) -> tuple[int, int]:
    return (
        session.scalar(select(func.count()).select_from(Document)) or 0,
        session.scalar(select(func.count()).select_from(DocumentLink)) or 0,
    )


def _complete_answers() -> dict[str, str]:
    return {
        "functional_manager": "Совпадает.",
        "direct_admin_reports": "Нет.",
        "total_reports": "0",
        "functional_reports": "Нет.",
        "position_purpose": "Помогает выпускать изменения без критичных дефектов.",
        "duties_results": json.dumps(
            [["Проверяет сценарии", "Критичные дефекты выявляются до релиза."]],
            ensure_ascii=False,
        ),
        "income_responsibility": "Не применимо.",
        "expense_budget_type": "Не применимо.",
        "expense_budget_volume": "Не применимо.",
        "expense_budget_management": "Не применимо.",
        "task_typicality": "Типовые с вариациями",
        "complex_task_example": "Выбирает критичные сценарии проверки при ограниченном времени.",
        "external_interactions": json.dumps(
            [["Подрядчик", "Тестовая среда", "Готовность стенда согласована."]],
            ensure_ascii=False,
        ),
        "internal_interactions": json.dumps(
            [["Разработчики", "Дефекты", "Исправления проверены."]],
            ensure_ascii=False,
        ),
        "government_interactions": "Не применимо.",
        "independent_decisions": "Самостоятельно оформляет дефекты и выбирает порядок проверки.",
        "approval_decisions": "Выпуск и приоритеты согласует руководитель.",
        "education": "Высшее (бакалавр / специалист / магистр)",
        "specialization": "Информационные системы или смежное направление.",
        "certification": "Не требуется.",
        "legal_knowledge": "Не требуется.",
        "methods_knowledge": "Тест-дизайн, чек-листы, регрессионное тестирование.",
        "technology_knowledge": "Баг-трекер, офисные приложения, базовые SQL-запросы.",
        "domain_context_knowledge": "Понимание жизненного цикла внутренних информационных систем.",
        "experience_requirements": json.dumps(
            [
                ["Профессиональный", "2", "Тестирование информационных систем."],
                ["Управленческий", "0", "Не требуется для должности."],
            ],
            ensure_ascii=False,
        ),
        "comments": "Дополнений нет.",
    }
