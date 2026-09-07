"""Async SQLAlchemy engine and session factory.

Uses the Supabase transaction pooler (port 6543) in production, which requires
disabling asyncpg's prepared-statement cache, since the pooler multiplexes
connections and does not keep server-side prepared statements alive across
checkouts. The setting is harmless against a direct local connection, so it is
applied uniformly.

**Connections are pooled and reused.** The original design used NullPool, which
opens a fresh connection per request. Measured against the production database,
that handshake — TCP, TLS and SCRAM authentication — costs ~1.8 s, while the
query itself costs ~0.35 s: every request was paying five times more to connect
than to ask. Reusing connections took a `SELECT 1` request from ~2200 ms to
~560 ms.

NullPool is the right choice for ephemeral, per-invocation runtimes such as edge
or serverless functions. This is a long-lived uvicorn process, where it is the
wrong one. The pool is deliberately small: one Render instance holds at most ten
client slots on the pooler.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every module's models."""


_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_size=5,
    max_overflow=5,
    # Recycled well before the pooler drops an idle client, which is what
    # pool_pre_ping would otherwise have to detect.
    pool_recycle=180,
    # Off on purpose: a pre-ping is a full round trip, and with the API in
    # Oregon and the database in São Paulo that costs ~650 ms on every single
    # request — more than the query it protects. Turn it back on (and raise
    # pool_recycle) once both live in the same region, where it costs ~2 ms.
    pool_pre_ping=False,
    connect_args={"statement_cache_size": 0},
    echo=False,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """FastAPI dependency yielding a session. Transactions are committed inside
    the service layer, never here."""
    async with SessionLocal() as session:
        yield session
