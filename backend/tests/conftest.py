"""Shared test fixtures.

Integration tests run against a real PostgreSQL database (kairos_test by
default). The schema is created once per session from the SQLAlchemy metadata
and dropped at the end; each test runs inside a transaction-scoped session that
is rolled back afterwards, so tests never see each other's writes.
"""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:1234@127.0.0.1:5432/kairos_test",
)


def _run_migrations(url: str) -> None:
    """Apply every Alembic migration up to head. Runs in a worker thread so the
    async env.py can own its own event loop (pytest-asyncio already holds one)."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture(scope="session")
async def engine():
    # Build the test schema from the migrations themselves, so any drift between
    # models and migrations surfaces here rather than in production.
    await asyncio.to_thread(_run_migrations, TEST_DATABASE_URL)

    eng = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """A session whose writes are rolled back at the end of each test.

    The session joins the fixture's outer transaction via a SAVEPOINT
    (join_transaction_mode="create_savepoint"), so commits made by the
    application code release and recreate the savepoint without ending the outer
    transaction, which is then rolled back to isolate each test.
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
def make_user(db: AsyncSession):
    """Factory that inserts a user directly, for arranging test preconditions."""
    from app.core.enums import GlobalRole, UserStatus
    from app.core.security import hash_password
    from app.modules.users.models import User

    async def _make(
        *,
        email: str,
        full_name: str = "Persona de Prueba",
        password: str = "unaClaveLarga123",
        global_role: GlobalRole = GlobalRole.MEMBER,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            global_role=global_role,
            status=status,
        )
        db.add(user)
        await db.flush()
        return user

    return _make


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
