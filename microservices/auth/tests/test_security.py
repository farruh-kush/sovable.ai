from __future__ import annotations

import pytest
from ai_routing_shared.exceptions import AuthenticationError
from auth.core.config import AuthSettings
from auth.db.models import UserAccount
from auth.security.dependencies import public_user_payload
from auth.security.identity import (
    create_access_token,
    decode_access_token,
    hash_password,
    normalize_email,
    normalize_phone,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)
    assert "correct horse" not in first


def test_password_policy_rejects_short_values() -> None:
    with pytest.raises(ValueError):
        hash_password("too-short")


def test_access_token_contains_role_but_not_secret_material() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    user = UserAccount(id="user_1", email="user@example.com", role="agent_creator")
    token = create_access_token(settings, user)
    claims = decode_access_token(settings, token)
    assert claims["sub"] == "user_1"
    assert claims["role"] == "agent_creator"
    assert "unit-test-secret" not in token


def test_invalid_access_token_is_authentication_error() -> None:
    settings = AuthSettings(secret_key="unit-test-secret")
    with pytest.raises(AuthenticationError):
        decode_access_token(settings, "not-a-token")


def test_normalization_is_deterministic() -> None:
    assert normalize_email("  User@Example.COM ") == "user@example.com"
    assert normalize_phone(" +1 415 555 0123 ") == "+14155550123"
    with pytest.raises(ValueError):
        normalize_email("not-an-email")
    with pytest.raises(ValueError):
        normalize_phone("4155550123")


def test_safe_user_payload_excludes_password_hash() -> None:
    user = UserAccount(
        id="user_1",
        email="user@example.com",
        password_hash="scrypt$private",
        role="user",
    )
    payload = public_user_payload(user)
    assert "password_hash" not in payload
    assert "scrypt$private" not in repr(payload)
