"""Billing Service database setup.

Phase 1 — Task 1.4: No ``create_all`` — schema managed by Alembic.

Author: Farruh
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..core.config import get_settings

_engine = None
_session_factory = None


async def init_db() -> None:
    """Initialise the async database engine."""
    global _engine, _session_factory
    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncSession:
    """Dependency: yield an async database session."""
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session
