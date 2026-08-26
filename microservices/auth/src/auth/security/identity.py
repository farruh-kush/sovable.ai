"""Security primitives for first-party identity and sessions."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from ai_routing_shared.exceptions import AuthenticationError

from ..core.config import AuthSettings

ALGORITHMS = ["HS256"]
ROLES = {"user", "org_admin", "agent_creator", "platform_controller"}
ACCOUNT_TYPE_TO_ROLE = {
    "user": "user",
    "admin": "org_admin",
    "creator": "agent_creator",
}


def now_utc() -> datetime:
    return datetime.now(UTC)


def secret_value(value: Any) -> str:
    """Return a secret setting without ever logging or serializing it."""
    return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    local, separator, domain = normalized.partition("@")
    if not separator or not local or not domain or len(normalized) > 320:
        raise ValueError("A valid email address is required")
    return normalized


def normalize_phone(value: str) -> str:
    compact = "".join(value.strip().split())
    if not compact.startswith("+") or not compact[1:].isdigit() or not 8 <= len(compact[1:]) <= 15:
        raise ValueError("Use an E.164 phone number such as +14155550123")
    return compact


def hash_value(settings: AuthSettings, value: str) -> str:
    """Hash bearer-like secrets with a server-side pepper; store only this digest."""
    return hashlib.sha256(f"{secret_value(settings.secret_key)}:{value}".encode()).hexdigest()


def hash_password(password: str) -> str:
    """Hash passwords with scrypt and a random salt.

    The encoded format is deliberately self-describing so cost parameters can be
    upgraded while old hashes remain verifiable.
    """
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Password must contain between 12 and 128 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded or not encoded.startswith("scrypt$"):
        return False
    try:
        _, n, r, p, salt_hex, digest_hex = encoded.split("$", 5)
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p)
        )
        return secrets.compare_digest(actual.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def random_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def create_access_token(settings: AuthSettings, user: Any) -> str:
    issued = now_utc()
    payload = {
        "iss": "sovable-auth",
        "aud": "sovable-api",
        "sub": user.id,
        "role": user.role,
        "email": user.email,
        "phone_verified": user.phone_verified,
        "iat": int(issued.timestamp()),
        "exp": int((issued + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret_value(settings.secret_key), algorithm="HS256")


def decode_access_token(settings: AuthSettings, token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            secret_value(settings.secret_key),
            algorithms=ALGORITHMS,
            audience="sovable-api",
            issuer="sovable-auth",
            options={"require": ["iss", "aud", "sub", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def provider_config(settings: AuthSettings, provider: str) -> dict[str, Any]:
    if provider == "google":
        return {
            "client_id": settings.google_client_id,
            "client_secret": secret_value(settings.google_client_secret),
            "redirect_uri": settings.google_redirect_uri
            or f"{settings.public_base_url}/auth/oauth/google/callback",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "issuer": "https://accounts.google.com",
            "scope": "openid email profile",
        }
    if provider == "apple":
        return {
            "client_id": settings.apple_client_id,
            "client_secret": "",
            "redirect_uri": settings.apple_redirect_uri
            or f"{settings.public_base_url}/auth/oauth/apple/callback",
            "authorization_endpoint": "https://appleid.apple.com/auth/authorize",
            "token_endpoint": "https://appleid.apple.com/auth/token",
            "jwks_uri": "https://appleid.apple.com/auth/keys",
            "issuer": "https://appleid.apple.com",
            "scope": "name email",
        }
    try:
        providers = json.loads(settings.oidc_providers_json or "{}")
        config = providers.get(provider)
    except (ValueError, TypeError):
        config = None
    if not isinstance(config, dict):
        raise AuthenticationError("Identity provider is not configured")
    return config
