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

Those measurements were taken with the API in Oregon and the database in São
Paulo. Both now live in us-east-1, which shrinks every figure above by roughly
two orders of magnitude — but the shape of the argument is unchanged, and the
pool still saves a handshake on every request.
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
    # Half an hour: long enough that recycling is rare, short enough to stay
    # well inside any idle timeout the pooler enforces.
    pool_recycle=1800,
    # A pre-ping is one round trip to the database. It was off while the API ran
    # in Oregon and the database in São Paulo, where that cost ~650 ms per
    # request — more than the query it was protecting. Both now live in
    # us-east-1, so it costs single-digit milliseconds and is worth having: it
    # turns a connection the pooler closed underneath us into a transparent
    # reconnect instead of a 500 for whoever made that request.
    pool_pre_ping=True,
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
