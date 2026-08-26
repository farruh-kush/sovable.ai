from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, Mock

import pytest
from ai_routing_shared.exceptions import EmailDeliveryError
from auth.api.identity import (
    ActivationComplete,
    ActivationStart,
    complete_email_activation,
    start_email_activation,
)
from auth.core.config import AuthSettings
from auth.db.models import EmailActivationToken, UserAccount
from auth.security.identity import hash_value, now_utc


class FakeRequest:
    headers: ClassVar[dict[str, str]] = {"user-agent": "pytest"}
    client: ClassVar[SimpleNamespace] = SimpleNamespace(host="127.0.0.1")


@pytest.mark.asyncio
async def test_activation_start_hashes_token_and_never_returns_it(monkeypatch) -> None:
    settings = AuthSettings(
        secret_key="unit-test-secret",
        frontend_base_url="https://example.test",
        directmail_timeout_seconds=2,
    )
    session = AsyncMock()
    session.add = Mock()
    session.scalar.return_value = None
    captured: dict[str, str] = {}

    async def fake_send(settings, recipient, activation_url):
        captured["recipient"] = recipient
        captured["url"] = activation_url

    monkeypatch.setattr("auth.api.identity.send_activation_email", fake_send)
    result = await start_email_activation(
        ActivationStart(email="User@Example.com", password="correct horse battery staple"),
        settings,
        session,
    )
    record = session.add.call_args.args[0]
    assert isinstance(record, EmailActivationToken)
    assert record.email == "user@example.com"
    assert record.token_hash != captured["url"].split("token=", 1)[1]
    assert record.token_hash == hash_value(settings, captured["url"].split("token=", 1)[1])
    assert "token" not in result
    assert captured["recipient"] == "user@example.com"


@pytest.mark.asyncio
async def test_activation_delivery_failure_does_not_expose_provider_details(monkeypatch) -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    session = AsyncMock()
    session.add = Mock()
    session.scalar.return_value = None

    async def fail(*args):
        raise EmailDeliveryError("provider access key must remain secret")

    monkeypatch.setattr("auth.api.identity.send_activation_email", fail)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await start_email_activation(
            ActivationStart(email="user@example.com"), settings, session
        )
    assert exc_info.value.status_code == 503
    assert "access key" not in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_expired_activation_token_is_rejected() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    token = EmailActivationToken(
        id="token_1",
        token_hash=hash_value(settings, "raw-token-value-012345678901234567890123456789"),
        email="user@example.com",
        expires_at=now_utc() - timedelta(seconds=1),
        consumed=False,
    )
    session = AsyncMock()
    session.scalar.return_value = token
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await complete_email_activation(
            ActivationComplete(token="raw-token-value-012345678901234567890123456789"),
            FakeRequest(),
            settings,
            session,
        )
    assert exc_info.value.status_code == 400
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_activation_token_is_consumed_once_and_replay_is_rejected() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    token = EmailActivationToken(
        id="token_1",
        token_hash=hash_value(settings, "raw-token-value-012345678901234567890123456789"),
        email="user@example.com",
        expires_at=now_utc() + timedelta(minutes=5),
        consumed=False,
        account_type="user",
    )
    user = UserAccount(id="user_1", email="user@example.com", email_verified=False, role="user")
    session = AsyncMock()
    session.add = Mock()
    session.scalar.side_effect = [token, user]
    result = await complete_email_activation(
        ActivationComplete(token="raw-token-value-012345678901234567890123456789"),
        FakeRequest(),
        settings,
        session,
    )
    assert token.consumed is True
    assert user.email_verified is True
    assert result["user"]["id"] == "user_1"
    assert session.commit.await_count >= 2

    replay_session = AsyncMock()
    replay_session.scalar.return_value = None
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await complete_email_activation(
            ActivationComplete(token="raw-token-value-012345678901234567890123456789"),
            FakeRequest(),
            settings,
            replay_session,
        )
    assert exc_info.value.status_code == 400
