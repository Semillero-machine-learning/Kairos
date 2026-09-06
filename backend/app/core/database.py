"""Async SQLAlchemy engine and session factory.

Uses the Supabase transaction pooler (port 6543) in production, which requires
disabling asyncpg's prepared-statement cache and using NullPool, since the
pooler multiplexes connections and does not keep server-side prepared statements
alive across checkouts. The same settings are harmless against a direct local
connection, so they are applied uniformly.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every module's models."""


_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    poolclass=NullPool,
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
