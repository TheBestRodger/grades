from __future__ import annotations

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import PROJECT_ROOT


def test_test_database_is_migrated_to_alembic_head_before_app_start(client: TestClient) -> None:
    config = Config(str(PROJECT_ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "migrations"))
    expected_head = ScriptDirectory.from_config(config).get_current_head()

    with client.app.state.database.engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert version == expected_head
