"""Alembic async migration environment.

The URL comes from a programmatic override (used by tests) when present, and
otherwise from the application settings, so migrations and the app always agree
on the target database and no secret is duplicated in alembic.ini.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import every module's models so their tables register on Base.metadata for
# autogenerate. Extended as each phase adds models; missing modules are ignored
# so the environment loads during early phases.
for _path in (
    "app.modules.users.models",
    "app.modules.auth.models",
    "app.modules.projects.models",
    "app.modules.tasks.models",
    "app.modules.notifications.models",
):
    try:
        __import__(_path)
    except ModuleNotFoundError:
        pass

target_metadata = Base.metadata


def _get_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
