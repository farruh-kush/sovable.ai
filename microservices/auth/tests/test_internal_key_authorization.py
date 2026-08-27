from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from ai_routing_shared.exceptions import AuthenticationError, AuthorisationError
from auth.core.config import AuthSettings
from auth.db.models import UserAccount
from auth.security import dependencies
from auth.security.dependencies import InternalServicePrincipal, require_key_management_actor
from starlette.requests import Request


def request(path: str) -> Request:
    return Request({"type": "http", "method": "POST", "path": path, "headers": []})


def settings() -> AuthSettings:
    return AuthSettings(AUTH_INTERNAL_SERVICE_KEY="test-internal-service-key")


@pytest.mark.asyncio
async def test_internal_key_route_accepts_only_matching_service_credential() -> None:
    actor = await require_key_management_actor(
        request("/internal/keys"),
        authorization=None,
        x_internal_service_key="test-internal-service-key",
        settings=settings(),
        session=AsyncMock(),
    )

    assert isinstance(actor, InternalServicePrincipal)
    assert actor.role == "platform_controller"


@pytest.mark.asyncio
async def test_invalid_internal_credential_is_rejected_without_jwt_fallback() -> None:
    with pytest.raises(AuthenticationError):
        await require_key_management_actor(
            request("/internal/keys"),
            authorization=None,
            x_internal_service_key="wrong-key",
            settings=settings(),
            session=AsyncMock(),
        )


@pytest.mark.asyncio
async def test_public_key_route_keeps_human_role_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    async def controller(*args: object, **kwargs: object) -> UserAccount:
        return UserAccount(id="controller", role="platform_controller")

    monkeypatch.setattr(dependencies, "current_user", controller)
    actor = await require_key_management_actor(
        request("/v1/keys"),
        authorization="Bearer human-token",
        x_internal_service_key="test-internal-service-key",
        settings=settings(),
        session=AsyncMock(),
    )
    assert isinstance(actor, UserAccount)
    assert actor.id == "controller"


@pytest.mark.asyncio
async def test_public_key_route_rejects_non_privileged_human(monkeypatch: pytest.MonkeyPatch) -> None:
    async def user(*args: object, **kwargs: object) -> UserAccount:
        return UserAccount(id="member", role="user")

    monkeypatch.setattr(dependencies, "current_user", user)
    with pytest.raises(AuthorisationError):
        await require_key_management_actor(
            request("/v1/keys"),
            authorization="Bearer human-token",
            x_internal_service_key="test-internal-service-key",
            settings=settings(),
            session=AsyncMock(),
        )
