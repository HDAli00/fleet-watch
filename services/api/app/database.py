"""Async database engine and session dependency."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator

import boto3
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

log = structlog.get_logger()

_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_db_url() -> str:
    """Resolve database URL from Secrets Manager or direct env override."""
    # Allow direct override for tests (set DATABASE_URL env var)
    direct_url = os.environ.get("DATABASE_URL")
    if direct_url:
        return direct_url

    secret_arn = os.environ.get("DB_SECRET_ARN", "")
    if not secret_arn:
        raise RuntimeError("DB_SECRET_ARN environment variable is required")

    client = boto3.client(
        "secretsmanager", region_name=os.environ.get("AWS_REGION_NAME", "eu-west-1")
    )
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])

    return (
        f"postgresql+asyncpg://{secret['username']}:{secret['password']}"
        f"@{secret['host']}:{secret.get('port', 5432)}/{secret.get('dbname', 'solar')}"
    )


def init_engine(db_url: str | None = None) -> None:
    """Initialise the async engine. Called once at app startup."""
    global _engine, _async_session_factory
    url = db_url or _get_db_url()
    _engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    _async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    log.info("db.engine.initialised")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an AsyncSession, rolls back on error."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialised — call init_engine() first")
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
