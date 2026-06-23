from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import PROJECT_ROOT

POSTGRES_POOL_SIZE = 5
POSTGRES_MAX_OVERFLOW = 10
POSTGRES_POOL_RECYCLE_SECONDS = 1_800


class Database:
    def __init__(self, database_url: str) -> None:
        engine_options = (
            {}
            if not database_url.startswith("postgresql")
            else {
                "pool_pre_ping": True,
                "pool_size": POSTGRES_POOL_SIZE,
                "max_overflow": POSTGRES_MAX_OVERFLOW,
                "pool_recycle": POSTGRES_POOL_RECYCLE_SECONDS,
            }
        )
        self.engine = create_engine(database_url, **engine_options)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    def migrate(self) -> None:
        config = Config(str(PROJECT_ROOT / "backend" / "alembic.ini"))
        config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "migrations"))
        config.set_main_option("sqlalchemy.url", self.engine.url.render_as_string(hide_password=False))
        config.attributes["database_url_was_explicit"] = True
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
