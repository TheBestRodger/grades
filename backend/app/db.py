from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import PROJECT_ROOT

SQLITE_BUSY_TIMEOUT_MS = 30_000


class Database:
    def __init__(self, database_url: str) -> None:
        is_sqlite = database_url.startswith("sqlite")
        connect_args = (
            {
                "check_same_thread": False,
                "timeout": SQLITE_BUSY_TIMEOUT_MS / 1000,
            }
            if is_sqlite
            else {}
        )
        self.engine = create_engine(database_url, connect_args=connect_args)
        if is_sqlite:
            self._configure_sqlite()
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    def _configure_sqlite(self) -> None:
        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def migrate(self) -> None:
        config = Config(str(PROJECT_ROOT / "backend" / "alembic.ini"))
        config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "migrations"))
        config.set_main_option("sqlalchemy.url", self.engine.url.render_as_string(hide_password=False))
        command.upgrade(config, "head")

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
