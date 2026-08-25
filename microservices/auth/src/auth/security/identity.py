"""Identity security helpers.
Author: Farruh
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException

from ..core.config import AuthSettings

ALGORITHMS = ["HS256"]


def now_utc() -> datetime:
    return datetime.now(UTC)


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if "@" not in value or len(value) > 320:
        raise HTTPException(status_code=422, detail="A valid email address is required")
    return value


def normalize_phone(value: str) -> str:
    compact = "".join(value.strip().split())
    if not compact.startswith("+") or not compact[1:].isdigit() or not 8 <= len(compact[1:]) <= 15:
        raise HTTPException(
            status_code=422, detail="Use an E.164 phone number such as +14155550123"
        )
    return compact


def hash_value(settings: AuthSettings, value: str) -> str:
    return hashlib.sha256(f"{settings.secret_key}:{value}".encode()).hexdigest()


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
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(settings: AuthSettings, token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=ALGORITHMS,
            audience="sovable-api",
            issuer="sovable-auth",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def provider_config(settings: AuthSettings, provider: str) -> dict[str, Any]:
    if provider == "google":
        return {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
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
        import json

        providers = json.loads(settings.oidc_providers_json or "{}")
        config = providers.get(provider)
    except (ValueError, TypeError):
        config = None
    if not isinstance(config, dict):
        raise HTTPException(status_code=404, detail="Identity provider is not configured")
    return config
