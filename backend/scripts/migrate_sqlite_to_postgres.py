from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Table, create_engine, text
from sqlalchemy.engine import Connection

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import Database
from app.models import Base


DEFAULT_SQLITE_PATH = BACKEND_ROOT / "data" / "demo.sqlite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely migrate legacy SQLite data into PostgreSQL."
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=DEFAULT_SQLITE_PATH,
        help="Path to the legacy SQLite database. The source file is never modified.",
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="PostgreSQL SQLAlchemy URL, for example postgresql+psycopg://user:pass@host:5432/db.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write data to PostgreSQL. Without this flag the script only validates the plan.",
    )
    parser.add_argument(
        "--replace-target",
        action="store_true",
        help="Dangerous: truncate application tables in PostgreSQL before importing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = args.sqlite_path.resolve()
    if not source_path.exists():
        raise SystemExit(f"SQLite source does not exist: {source_path}")
    if not args.database_url.startswith("postgresql"):
        raise SystemExit("Target --database-url must point to PostgreSQL.")

    with tempfile.TemporaryDirectory(prefix="grades-mgtu-sqlite-copy-") as temp_dir:
        sqlite_copy = Path(temp_dir) / source_path.name
        shutil.copy2(source_path, sqlite_copy)
        sqlite_url = f"sqlite:///{sqlite_copy.as_posix()}"

        print(f"Source copy: {sqlite_copy}")
        print("Upgrading copied SQLite source to current Alembic head...")
        Database(sqlite_url).migrate()

        source = sqlite3.connect(f"file:{sqlite_copy.as_posix()}?mode=ro", uri=True)
        source.row_factory = sqlite3.Row
        target = create_engine(args.database_url, pool_pre_ping=True)

        print("Upgrading PostgreSQL target to current Alembic head...")
        Database(args.database_url).migrate()

        tables = application_tables()
        source_counts = count_source_rows(source, tables)
        print_counts("SQLite source rows", source_counts)

        with target.begin() as connection:
            target_counts = count_target_rows(connection, tables)
            if any(count > 0 for count in target_counts.values()):
                if not args.replace_target:
                    print_counts("PostgreSQL target rows", target_counts)
                    raise SystemExit(
                        "PostgreSQL target is not empty. Re-run with --replace-target "
                        "only after taking a backup and confirming overwrite is intended."
                    )
                if not args.apply:
                    print("Target has data; --replace-target would truncate it during --apply.")
                else:
                    truncate_target(connection, tables)

            if not args.apply:
                print("Dry run complete. Re-run with --apply to import into PostgreSQL.")
                return

            for table in tables:
                rows = source_rows(source, table)
                if rows:
                    connection.execute(table.insert(), rows)
                    print(f"Imported {len(rows)} rows into {table.name}")

            reset_postgres_sequences(connection, tables)
            verify_rows(source, connection, tables)

        print("Migration committed. PostgreSQL target matches SQLite source.")


def application_tables() -> list[Table]:
    return [table for table in Base.metadata.sorted_tables if table.name != "alembic_version"]


def count_source_rows(source: sqlite3.Connection, tables: Iterable[Table]) -> dict[str, int]:
    return {
        table.name: int(source.execute(f'SELECT COUNT(*) FROM "{table.name}"').fetchone()[0])
        for table in tables
    }


def count_target_rows(connection: Connection, tables: Iterable[Table]) -> dict[str, int]:
    return {
        table.name: int(connection.execute(sa.select(sa.func.count()).select_from(table)).scalar_one())
        for table in tables
    }


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(title + ":")
    for table_name, count in counts.items():
        print(f"  {table_name}: {count}")


def source_rows(source: sqlite3.Connection, table: Table) -> list[dict[str, Any]]:
    column_names = [column.name for column in table.columns]
    select_columns = ", ".join(f'"{name}"' for name in column_names)
    rows = source.execute(f'SELECT {select_columns} FROM "{table.name}"').fetchall()
    return [
        {
            column.name: convert_source_value(column, row[column.name])
            for column in table.columns
        }
        for row in rows
    ]


def convert_source_value(column: sa.Column[Any], value: Any) -> Any:
    if value is None:
        return None
    column_type = column.type
    if isinstance(column_type, Boolean):
        return bool(value)
    if isinstance(column_type, Integer):
        return int(value)
    if isinstance(column_type, Float):
        return float(value)
    if isinstance(column_type, DateTime):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    if isinstance(column_type, Date):
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))
    return value


def truncate_target(connection: Connection, tables: list[Table]) -> None:
    preparer = connection.dialect.identifier_preparer
    table_list = ", ".join(preparer.quote(table.name) for table in tables)
    connection.execute(text(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"))
    print("PostgreSQL target application tables truncated.")


def reset_postgres_sequences(connection: Connection, tables: Iterable[Table]) -> None:
    for table in tables:
        primary_key = list(table.primary_key.columns)
        if len(primary_key) != 1 or not isinstance(primary_key[0].type, Integer):
            continue
        column = primary_key[0]
        sequence = connection.execute(
            text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
            {"table_name": table.name, "column_name": column.name},
        ).scalar()
        if sequence is None:
            continue
        max_id = connection.execute(sa.select(sa.func.max(column))).scalar()
        connection.execute(
            text("SELECT setval(:sequence_name, :sequence_value, :is_called)"),
            {
                "sequence_name": sequence,
                "sequence_value": int(max_id or 1),
                "is_called": max_id is not None,
            },
        )


def verify_rows(source: sqlite3.Connection, target: Connection, tables: Iterable[Table]) -> None:
    for table in tables:
        expected = normalized_source_rows(source, table)
        actual = normalized_target_rows(target, table)
        if expected != actual:
            raise RuntimeError(f"Verification failed for table {table.name}")
        print(f"Verified {table.name}: {len(actual)} rows")


def normalized_source_rows(source: sqlite3.Connection, table: Table) -> list[tuple[Any, ...]]:
    rows = source_rows(source, table)
    return normalize_rows(table, rows)


def normalized_target_rows(target: Connection, table: Table) -> list[tuple[Any, ...]]:
    rows = [dict(row) for row in target.execute(sa.select(*table.columns)).mappings().all()]
    return normalize_rows(table, rows)


def normalize_rows(table: Table, rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    normalized = [
        tuple(normalize_value(row[column.name]) for column in table.columns)
        for row in rows
    ]
    return sorted(normalized, key=repr)


def normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None).isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


if __name__ == "__main__":
    main()
