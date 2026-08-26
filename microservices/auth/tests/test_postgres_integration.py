from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_URL = os.getenv("AUTH_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set AUTH_TEST_DATABASE_URL or TEST_DATABASE_URL to run PostgreSQL integration tests",
)


@pytest.mark.asyncio
async def test_auth_postgres_is_reachable_and_migration_schema_exists() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("SELECT 1"))).scalar_one() == 1
            tables = {
                row[0]
                for row in (
                    await connection.execute(
                        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                    )
                ).all()
            }
        expected = {
            "user_accounts",
            "email_activation_tokens",
            "user_identities",
            "auth_sessions",
            "api_keys",
        }
        assert expected <= tables
    finally:
        await engine.dispose()
