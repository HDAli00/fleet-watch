"""Shared pytest fixtures: testcontainers Postgres + FastAPI async test client."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from testcontainers.postgres import PostgresContainer

import app.models  # noqa: F401 — register all SA metadata
from app.database import get_db
from app.main import app


@pytest.fixture(scope="session")
def event_loop_policy() -> Any:
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def async_db_url(postgres_container: PostgresContainer) -> str:
    url = postgres_container.get_connection_url()
    return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")


@pytest_asyncio.fixture(scope="session")
async def db_engine(async_db_url: str) -> Any:
    engine = create_async_engine(async_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return engine


@pytest_asyncio.fixture
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()  # isolate each test


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async test client with DB session override."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()
