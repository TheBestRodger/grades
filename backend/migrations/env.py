from logging.config import fileConfig
import os

from alembic import context
import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool

from app.models import Base


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

configured_url = config.get_main_option("sqlalchemy.url")
if (
    not config.attributes.get("database_url_was_explicit")
    and (not configured_url or "change-me-in-.env" in configured_url)
    and (database_url := os.environ.get("DATABASE_URL"))
):
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def ensure_version_table_uses_wide_revision_ids(connection) -> None:
    table_name = "alembic_version"
    inspector = sa.inspect(connection)
    if table_name not in inspector.get_table_names():
        sa.Table(
            table_name,
            sa.MetaData(),
            sa.Column("version_num", sa.String(255), nullable=False, primary_key=True),
        ).create(connection)
        return

    if connection.dialect.name == "postgresql":
        connection.execute(
            sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")
        )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        ensure_version_table_uses_wide_revision_ids(connection)
        if connection.in_transaction():
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
