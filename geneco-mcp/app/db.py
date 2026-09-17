"""Async SQLAlchemy engine/session wiring.

Mirrors duta-ilmu's integration-hub ``db.py`` pattern, minus the shared-
cluster schema relocation (this is a dedicated single-purpose database, not
one schema among several on a shared cluster).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
