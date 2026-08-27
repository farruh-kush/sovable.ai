from __future__ import annotations

import httpx
import pytest
import respx

from gateway.api.v1.keys import CreateKeyRequest, create_key, list_keys, revoke_key
from gateway.core.config import GatewaySettings


def settings() -> GatewaySettings:
    return GatewaySettings(
        ADMIN_API_KEY="test-admin-key",
        AUTH_SERVICE_URL="http://auth:8001",
        AUTH_INTERNAL_SERVICE_KEY="test-internal-service-key",
    )


@pytest.mark.asyncio
@respx.mock
async def test_gateway_proxies_a_complete_internal_key_lifecycle() -> None:
    create = respx.post("http://auth:8001/internal/keys").mock(
        return_value=httpx.Response(
            200,
            json={"id": "key_temporary", "key": "sk_test_not_a_real_key", "name": "e2e", "tier": "free"},
        )
    )
    listed = respx.get("http://auth:8001/internal/keys").mock(
        return_value=httpx.Response(
            200,
            json={"keys": [{"id": "key_temporary", "name": "e2e", "is_active": True}]},
        )
    )
    revoke = respx.delete("http://auth:8001/internal/keys/key_temporary").mock(
        return_value=httpx.Response(200, json={"status": "revoked", "id": "key_temporary"})
    )

    created = await create_key(
        CreateKeyRequest(name="e2e", monthly_budget_usd=0.01, allowed_models=["qwen-plus"]),
        x_admin_key="test-admin-key",
        settings=settings(),
    )
    keys = await list_keys(x_admin_key="test-admin-key", settings=settings())
    revoked = await revoke_key("key_temporary", x_admin_key="test-admin-key", settings=settings())

    assert created["id"] == "key_temporary"
    assert keys == {"keys": [{"id": "key_temporary", "name": "e2e", "is_active": True}]}
    assert revoked == {"status": "revoked", "id": "key_temporary"}
    for route in (create, listed, revoke):
        assert route.called
        assert route.calls[0].request.headers["X-Internal-Service-Key"] == "test-internal-service-key"
