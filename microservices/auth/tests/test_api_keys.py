from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from ai_routing_shared.exceptions import AuthorisationError
from ai_routing_shared.models import ApiKeyTier
from auth.api.keys import CreateKeyRequest, create_key, list_keys, revoke_key
from auth.api.validate import ValidateKeyRequest, validate_key
from auth.db.models import ApiKeyRecord, UserAccount


@pytest.mark.asyncio
async def test_create_key_returns_raw_key_once_and_persists_only_hash() -> None:
    session = AsyncMock()
    session.add = Mock()
    actor = UserAccount(id="controller", role="platform_controller")
    response = await create_key(
        CreateKeyRequest(name="production", tier=ApiKeyTier.PRO), session, actor
    )
    record = session.add.call_args.args[0]
    assert response.key.startswith("sk-")
    assert record.key_hash != response.key
    assert len(record.key_hash) == 64
    assert response.key not in repr(record)


@pytest.mark.asyncio
async def test_org_admin_can_only_create_own_key() -> None:
    session = AsyncMock()
    actor = UserAccount(id="admin", role="org_admin")
    with pytest.raises(AuthorisationError):
        await create_key(CreateKeyRequest(name="other", user_id="other-user"), session, actor)


@pytest.mark.asyncio
async def test_list_keys_is_metadata_only_and_scoped_for_org_admin() -> None:
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = [
        ApiKeyRecord(
            id="key_1",
            name="my-key",
            key_hash="a" * 64,
            user_id="admin",
            tier="free",
            is_active=True,
        )
    ]
    session.execute.return_value = result
    actor = UserAccount(id="admin", role="org_admin")
    payload = await list_keys(session, actor)
    assert payload["keys"][0]["id"] == "key_1"
    assert "key_hash" not in repr(payload)
    assert "key" not in payload["keys"][0]


@pytest.mark.asyncio
async def test_revoke_key_is_owner_scoped() -> None:
    session = AsyncMock()
    session.get.return_value = ApiKeyRecord(
        id="key_1", name="someone", key_hash="a" * 64, user_id="other", tier="free"
    )
    actor = UserAccount(id="admin", role="org_admin")
    with pytest.raises(AuthorisationError):
        await revoke_key("key_1", session, actor)


@pytest.mark.asyncio
async def test_validate_key_returns_shared_principal_and_updates_last_used() -> None:
    session = AsyncMock()
    record = ApiKeyRecord(
        id="key_1",
        name="gateway",
        key_hash="a" * 64,
        user_id="u1",
        tier="free",
        requests_per_minute=60,
        requests_per_day=2000,
        is_active=True,
    )
    from ai_routing_shared.utils import hash_api_key

    record.key_hash = hash_api_key("sk-test-value")
    execute_result = Mock()
    execute_result.scalar_one_or_none.return_value = record
    session.execute.return_value = execute_result
    result = await validate_key(ValidateKeyRequest(raw_key="sk-test-value"), session)
    assert result.id == "key_1"
    assert result.is_active is True
    assert record.last_used_at is not None
    session.commit.assert_awaited_once()
