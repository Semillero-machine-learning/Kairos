"""Shared test fixtures.

Integration tests run against a real PostgreSQL database (kairos_test by
default). The schema is created once per session from the SQLAlchemy metadata
and dropped at the end; each test runs inside a transaction-scoped session that
is rolled back afterwards, so tests never see each other's writes.
"""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

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


@pytest.fixture(autouse=True)
def no_real_emails(monkeypatch):
    """Ninguna prueba manda un correo de verdad.

    El `.env` de desarrollo puede traer una `RESEND_API_KEY` válida, y sin esto
    la suite le mandaría correos a direcciones inventadas cada vez que corre:
    lento, dependiente de la red, y con la cuota de un proveedor real de por
    medio. Con la clave vacía el cliente registra el envío en el log y devuelve
    éxito, que es el camino que las pruebas quieren ejercitar.

    Las pruebas que necesitan un fallo del proveedor parchean `EmailClient`
    directamente y este ajuste no les estorba.
    """
    monkeypatch.setattr(get_settings(), "resend_api_key", "", raising=False)


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
def auth_header(client):
    """Log a user in and return the Authorization header for them."""

    async def _header(email: str, password: str = "unaClaveLarga123") -> dict[str, str]:
        response = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _header


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
