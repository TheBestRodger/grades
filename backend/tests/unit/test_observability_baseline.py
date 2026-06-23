from __future__ import annotations

from pathlib import Path
import logging
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_database
from app.core.config import Settings
from app.core.observability import (
    REQUEST_ID_HEADER,
    JsonRequestLogFormatter,
)
from app.main import create_app
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


def test_request_id_header_is_propagated_and_readiness_checks_db(tmp_path: Path) -> None:
    with TestClient(app_for_test(tmp_path)) as client:
        liveness = client.get("/api/health/live")
        assert liveness.status_code == 200
        assert liveness.json() == {"status": "alive"}

        readiness = client.get(
            "/api/health/ready",
            headers={REQUEST_ID_HEADER: "test-request-id"},
        )
        assert readiness.status_code == 200
        assert readiness.headers[REQUEST_ID_HEADER] == "test-request-id"
        assert readiness.json() == {
            "status": "ready",
            "checks": {
                "database": "ok",
            },
        }

        legacy_readiness = client.get("/api/readiness")
        assert legacy_readiness.status_code == 200
        assert legacy_readiness.json() == readiness.json()


def test_readiness_fails_but_liveness_survives_database_error(tmp_path: Path) -> None:
    app = app_for_test(tmp_path)

    class FailingEngine:
        def connect(self):
            raise SQLAlchemyError("database unavailable")

    app.dependency_overrides[get_database] = lambda: SimpleNamespace(engine=FailingEngine())

    with TestClient(app) as client:
        readiness = client.get("/api/health/ready")
        assert readiness.status_code == 503
        assert readiness.json()["detail"] == {
            "status": "not_ready",
            "checks": {"database": "error"},
        }

        liveness = client.get("/api/health/live")
        assert liveness.status_code == 200
        assert liveness.json() == {"status": "alive"}


def test_request_log_formatter_outputs_expected_json_fields() -> None:
    record = logging.LogRecord(
        name="app.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.method = "GET"
    record.path = "/api/health"
    record.status_code = 200
    record.duration_ms = 12.5
    record.request_id = "abc"

    rendered = JsonRequestLogFormatter().format(record)

    assert '"event":"http_request"' in rendered
    assert '"method":"GET"' in rendered
    assert '"path":"/api/health"' in rendered
    assert '"status_code":200' in rendered
    assert '"duration_ms":12.5' in rendered
    assert '"request_id":"abc"' in rendered
