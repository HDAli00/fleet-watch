"""Alembic environment — async engine via asyncpg."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

# Load all models so metadata is populated
import app.models  # noqa: F401
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url() -> str:
    """Resolve DB URL for migrations — prefers DATABASE_URL env var."""
    direct = os.environ.get("DATABASE_URL")
    if direct:
        # Alembic needs postgresql+asyncpg:// scheme
        return direct.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise RuntimeError("Set DATABASE_URL env var before running alembic")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    engine = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
