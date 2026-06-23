from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError


DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://grades_mgtu:grades_mgtu@127.0.0.1:6432/postgres"
)


def _maintenance_url() -> URL:
    raw_url = os.environ.get("BACKEND_TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    url = make_url(raw_url)
    if not url.drivername.startswith("postgresql"):
        pytest.skip("B10 API/integration tests require PostgreSQL test database URL.")
    return url.set(database=os.environ.get("BACKEND_TEST_MAINTENANCE_DB", url.database or "postgres"))


def _quote_database_name(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe test database name: {name}")
    return f'"{name}"'


@pytest.fixture()
def postgres_database_url() -> Iterator[str]:
    admin_url = _maintenance_url()
    db_name = f"grades_mgtu_test_{uuid4().hex}"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    quoted_db_name = _quote_database_name(db_name)

    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE {quoted_db_name}"))
    except SQLAlchemyError as exc:
        admin_engine.dispose()
        pytest.skip(f"PostgreSQL test database is unavailable: {exc}")

    try:
        yield admin_url.set(database=db_name).render_as_string(hide_password=False)
    finally:
        try:
            with admin_engine.connect() as connection:
                connection.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = :database_name
                          AND pid <> pg_backend_pid()
                        """
                    ),
                    {"database_name": db_name},
                )
                connection.execute(text(f"DROP DATABASE IF EXISTS {quoted_db_name}"))
        finally:
            admin_engine.dispose()
