"""Shared test fixtures.

Integration tests run against a real PostgreSQL database (kairos_test by
default). The schema is created once per session from the SQLAlchemy metadata
and dropped at the end; each test runs inside a transaction-scoped session that
is rolled back afterwards, so tests never see each other's writes.
"""

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:1234@127.0.0.1:5432/kairos_test",
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    # Import every module's models so they register on the shared metadata,
    # then create the schema. Models are added as the phases progress.
    from app.core.database import Base

    _import_all_models()
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """A session whose writes are rolled back at the end of each test."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection, expire_on_commit=False, autoflush=False
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client whose get_db dependency is bound to the rolled-back session."""
    from app.core.database import get_db
    from app.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with LifespanManager(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                yield ac
    finally:
        app.dependency_overrides.clear()


def _import_all_models() -> None:
    """Import model modules so their tables register on Base.metadata.

    Extended as each phase adds models. Missing modules are ignored so the
    suite runs during early phases.
    """
    module_paths = [
        "app.modules.users.models",
        "app.modules.auth.models",
        "app.modules.notifications.models",
    ]
    for path in module_paths:
        try:
            __import__(path)
        except ModuleNotFoundError:
            pass
