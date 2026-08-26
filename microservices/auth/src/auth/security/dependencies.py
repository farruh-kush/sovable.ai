"""FastAPI dependencies for authenticated identity and role checks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ai_routing_shared.exceptions import AuthenticationError, AuthorisationError
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import AuthSettings, get_settings
from ..db.database import get_session
from ..db.models import UserAccount
from .identity import decode_access_token


async def current_user(
    authorization: str | None = Header(default=None),
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> UserAccount:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Bearer access token required")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AuthenticationError("Bearer access token required")
    claims = decode_access_token(settings, token)
    user = await session.get(UserAccount, claims["sub"])
    if not user or user.status != "active":
        raise AuthenticationError("User account is inactive")
    return user


def require_roles(*roles: str) -> Callable[..., Awaitable[UserAccount]]:
    async def dependency(user: UserAccount = Depends(current_user)) -> UserAccount:
        if user.role not in roles:
            raise AuthorisationError("You do not have permission to perform this action.")
        return user

    return dependency


async def optional_current_user(
    authorization: str | None = Header(default=None),
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> UserAccount | None:
    if not authorization:
        return None
    return await current_user(authorization, settings, session)


def public_user_payload(user: UserAccount) -> dict[str, Any]:
    """Return a safe account representation; never include password or token material."""
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "email_verified": user.email_verified,
        "phone_e164": user.phone_e164,
        "phone_verified": user.phone_verified,
        "role": user.role,
        "status": user.status,
    }
