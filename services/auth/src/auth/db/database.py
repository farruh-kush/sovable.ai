"""Auth Service database setup using SQLAlchemy async + Alembic migrations.

Phase 1 — Task 1.4: The application no longer calls ``create_all`` on startup.
Schema management is handled exclusively by Alembic migrations, which run via
the Docker entrypoint before the application starts.

Author: Farruh
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..core.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all Auth Service models."""
    pass


_engine = None
_session_factory = None


async def init_db() -> None:
    """Initialise the async database engine and session factory.

    NOTE: This function does NOT call ``create_all``. All schema changes
    must go through Alembic migrations (``alembic upgrade head``).
    """
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
    assert _session_factory is not None, "Database not initialised. Call init_db() first."
    async with _session_factory() as session:
        yield session
