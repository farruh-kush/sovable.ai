from __future__ import annotations

import asyncio

import pytest
from ai_routing_shared.exceptions import EmailDeliveryError
from auth.core.config import AuthSettings
from auth.security import email


@pytest.mark.asyncio
async def test_directmail_success(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_send(settings, recipient, subject, text, html):
        called.update(recipient=recipient, subject=subject, text=text, html=html)

    monkeypatch.setattr(email, "_send_directmail", fake_send)
    settings = AuthSettings(
        directmail_access_key_id="access-key-id",
        directmail_access_key_secret="access-key-secret",
        directmail_account_name="noreply@example.com",
        directmail_timeout_seconds=2,
    )
    await email.send_activation_email(settings, "user@example.com", "https://example.test/activate")
    assert called["recipient"] == "user@example.com"
    assert "https://example.test/activate" in called["text"]


@pytest.mark.asyncio
async def test_directmail_provider_failure_is_normalized(monkeypatch) -> None:
    def fail(*args):
        raise RuntimeError("provider secret access-key-secret leaked")

    monkeypatch.setattr(email, "_send_directmail", fail)
    settings = AuthSettings(
        directmail_access_key_id="access-key-id",
        directmail_access_key_secret="access-key-secret",
        directmail_account_name="noreply@example.com",
    )
    with pytest.raises(EmailDeliveryError) as exc_info:
        await email.send_activation_email(
            settings, "user@example.com", "https://example.test/activate"
        )
    assert "access-key-secret" not in str(exc_info.value)
    assert str(exc_info.value) == "Alibaba DirectMail request failed"


@pytest.mark.asyncio
async def test_directmail_timeout_is_normalized(monkeypatch) -> None:
    async def never_finishes(*args, **kwargs):
        await asyncio.sleep(10)

    def fake_to_thread(*args, **kwargs):
        return never_finishes()

    monkeypatch.setattr(email.asyncio, "to_thread", fake_to_thread)

    async def fake_wait_for(awaitable, timeout):
        awaitable.close()
        raise TimeoutError

    monkeypatch.setattr(email.asyncio, "wait_for", fake_wait_for)
    settings = AuthSettings(
        directmail_access_key_id="access-key-id",
        directmail_access_key_secret="access-key-secret",
        directmail_account_name="noreply@example.com",
        directmail_timeout_seconds=1,
    )
    with pytest.raises(EmailDeliveryError, match="timed out"):
        await email.send_activation_email(
            settings, "user@example.com", "https://example.test/activate"
        )


def test_settings_repr_redacts_directmail_secrets() -> None:
    settings = AuthSettings(
        directmail_access_key_id="access-key-id",
        directmail_access_key_secret="access-key-secret",
    )
    rendered = repr(settings)
    assert "access-key-secret" not in rendered
    assert "access-key-id" not in rendered
