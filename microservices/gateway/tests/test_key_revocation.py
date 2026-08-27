from __future__ import annotations

import httpx
import pytest
import respx
from ai_routing_shared.exceptions import AuthorisationError
from fastapi.responses import JSONResponse

from gateway.api.v1.keys import revoke_key
from gateway.core.config import GatewaySettings


def settings() -> GatewaySettings:
    return GatewaySettings(
        ADMIN_API_KEY="test-admin-key",
        AUTH_SERVICE_URL="http://auth:8001",
    )


@pytest.mark.asyncio
@respx.mock
async def test_revoke_key_forwards_to_auth_and_returns_safe_metadata() -> None:
    revoke = respx.delete("http://auth:8001/internal/keys/key_temporary").mock(
        return_value=httpx.Response(200, json={"status": "revoked", "id": "key_temporary"})
    )

    response = await revoke_key(
        "key_temporary",
        x_admin_key="test-admin-key",
        settings=settings(),
    )

    assert response == {"status": "revoked", "id": "key_temporary"}
    assert revoke.called


@pytest.mark.asyncio
@respx.mock
async def test_revoke_key_rejects_invalid_admin_key_before_auth_call() -> None:
    revoke = respx.delete("http://auth:8001/internal/keys/key_temporary").mock(
        return_value=httpx.Response(200, json={"status": "revoked", "id": "key_temporary"})
    )

    with pytest.raises(AuthorisationError):
        await revoke_key(
            "key_temporary",
            x_admin_key="invalid-admin-key",
            settings=settings(),
        )

    assert not revoke.called


@pytest.mark.asyncio
@respx.mock
async def test_revoke_key_maps_missing_key_without_leaking_upstream_fields() -> None:
    respx.delete("http://auth:8001/internal/keys/key_missing").mock(
        return_value=httpx.Response(404, json={"detail": "API key not found", "internal": "do-not-leak"})
    )

    response = await revoke_key(
        "key_missing",
        x_admin_key="test-admin-key",
        settings=settings(),
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert response.body == b'{"error":{"code":"upstream_rejected","message":"API key not found"}}'
    assert b"do-not-leak" not in response.body
