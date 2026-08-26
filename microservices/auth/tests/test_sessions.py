from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, Mock

import pytest
from ai_routing_shared.exceptions import AuthenticationError
from auth.api.identity import PasswordLoginRequest, RefreshRequest, login, refresh
from auth.core.config import AuthSettings
from auth.db.models import AuthSession, UserAccount
from auth.security.identity import hash_password, hash_value, now_utc


class Request:
    headers: ClassVar[dict[str, str]] = {"user-agent": "pytest"}
    client: ClassVar[SimpleNamespace] = SimpleNamespace(host="127.0.0.1")


@pytest.mark.asyncio
async def test_password_login_issues_access_and_refresh_tokens() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    user = UserAccount(
        id="u1",
        email="user@example.com",
        password_hash=hash_password("correct horse battery staple"),
        email_verified=True,
        status="active",
        role="user",
    )
    session = AsyncMock()
    session.scalar.return_value = user
    session.add = Mock()
    result = await login(
        PasswordLoginRequest(email="USER@example.com", password="correct horse battery staple"),
        Request(),
        settings,
        session,
    )
    assert result["token_type"] == "Bearer"
    assert result["access_token"]
    assert result["refresh_token"]
    assert result["user"]["email"] == "user@example.com"
    assert "password_hash" not in repr(result)


@pytest.mark.asyncio
async def test_password_login_does_not_enumerate_unknown_or_unverified_accounts() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    session = AsyncMock()
    session.scalar.return_value = None
    with pytest.raises(AuthenticationError) as missing:
        await login(
            PasswordLoginRequest(email="missing@example.com", password="wrong"),
            Request(),
            settings,
            session,
        )
    unverified = UserAccount(
        id="u1",
        email="user@example.com",
        password_hash=hash_password("correct horse battery staple"),
        email_verified=False,
    )
    session.scalar.return_value = unverified
    with pytest.raises(AuthenticationError) as unverified_error:
        await login(
            PasswordLoginRequest(email="user@example.com", password="correct horse battery staple"),
            Request(),
            settings,
            session,
        )
    assert str(missing.value) == str(unverified_error.value) == "Invalid email or password"


@pytest.mark.asyncio
async def test_refresh_rotates_and_revokes_old_token() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    user = UserAccount(
        id="u1", email="user@example.com", email_verified=True, status="active", role="user"
    )
    raw = "refresh-token-value-012345678901234567890123456789"
    record = AuthSession(
        id="s1",
        user_id="u1",
        refresh_token_hash=hash_value(settings, raw),
        expires_at=now_utc() + timedelta(days=1),
        revoked_at=None,
    )
    session = AsyncMock()
    session.scalar.return_value = record
    session.get.return_value = user
    session.add = Mock()
    result = await refresh(RefreshRequest(refresh_token=raw), Request(), settings, session)
    assert record.revoked_at is not None
    assert result["refresh_token"] != raw
    assert session.commit.await_count >= 2


@pytest.mark.asyncio
async def test_expired_refresh_token_is_rejected_without_session_creation() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    raw = "refresh-token-value-012345678901234567890123456789"
    record = AuthSession(
        id="s1",
        user_id="u1",
        refresh_token_hash=hash_value(settings, raw),
        expires_at=now_utc() - timedelta(seconds=1),
        revoked_at=None,
    )
    session = AsyncMock()
    session.scalar.return_value = record
    with pytest.raises(AuthenticationError):
        await refresh(RefreshRequest(refresh_token=raw), Request(), settings, session)
    session.add.assert_not_called()
