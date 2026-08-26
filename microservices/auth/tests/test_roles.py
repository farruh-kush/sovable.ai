from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from ai_routing_shared.exceptions import AuthenticationError, AuthorisationError
from auth.api.identity import AccountLinkRequest, RoleUpdateRequest, link_account, update_role
from auth.core.config import AuthSettings
from auth.db.models import UserAccount, UserIdentity
from auth.security.dependencies import current_user, require_roles


@pytest.mark.asyncio
async def test_current_user_rejects_missing_bearer() -> None:
    with pytest.raises(AuthenticationError):
        await current_user(None, AuthSettings(secret_key="unit-test-secret"), AsyncMock())


@pytest.mark.asyncio
async def test_role_dependency_isolates_users() -> None:
    dependency = require_roles("platform_controller")
    user = UserAccount(id="u1", role="user")
    with pytest.raises(AuthorisationError):
        await dependency(user)
    controller = UserAccount(id="u2", role="platform_controller")
    assert await dependency(controller) is controller


@pytest.mark.asyncio
async def test_org_admin_cannot_grant_platform_controller() -> None:
    actor = UserAccount(id="admin", role="org_admin")
    target = UserAccount(id="target", role="user")
    session = AsyncMock()
    session.get.return_value = target
    with pytest.raises(AuthorisationError):
        await update_role("target", RoleUpdateRequest(role="platform_controller"), session, actor)
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_account_linking_requires_authenticated_matching_email() -> None:
    user = UserAccount(id="u1", email="user@example.com", role="user")
    session = AsyncMock()
    session.scalar.return_value = None
    session.add = lambda obj: None
    with pytest.raises(AuthorisationError):
        await link_account(
            AccountLinkRequest(
                provider="google", provider_subject="sub-1", email="other@example.com"
            ),
            user,
            session,
        )


@pytest.mark.asyncio
async def test_account_linking_stores_provider_subject_not_credentials() -> None:
    user = UserAccount(id="u1", email="user@example.com", role="user")
    session = AsyncMock()
    session.scalar.return_value = None
    added: list[UserIdentity] = []
    session.add = added.append
    result = await link_account(
        AccountLinkRequest(provider="google", provider_subject="sub-1"), user, session
    )
    assert result == {"status": "linked", "provider": "google"}
    assert added[0].provider_subject == "sub-1"
    assert not hasattr(added[0], "access_key")
