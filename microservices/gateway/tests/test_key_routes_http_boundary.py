from __future__ import annotations

import httpx
import pytest
import respx

from gateway.core.config import get_settings
from gateway.main import create_app


@pytest.fixture(autouse=True)
def isolated_gateway_settings(monkeypatch: pytest.MonkeyPatch):
    """Use non-production settings and clear the cached settings around each case."""

    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("AUTH_INTERNAL_SERVICE_KEY", "test-internal-service-key")
    monkeypatch.setenv("AUTH_SERVICE_URL", "http://auth:8001")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_key_lifecycle_routes_use_internal_auth_proxy_at_http_boundary() -> None:
    """The public Gateway endpoints must dispatch to Auth's internal key lifecycle API."""

    list_route = respx.get("http://auth:8001/internal/keys").mock(
        return_value=httpx.Response(200, json={"keys": []})
    )
    create_route = respx.post("http://auth:8001/internal/keys").mock(
        return_value=httpx.Response(
            200,
            json={"id": "key_test_1", "key": "sk_test_only", "name": "verification", "tier": "free"},
        )
    )
    revoke_route = respx.delete("http://auth:8001/internal/keys/key_test_1").mock(
        return_value=httpx.Response(200, json={"status": "revoked", "id": "key_test_1"})
    )
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://gateway") as client:
        list_response = await client.get("/v1/keys", headers={"X-Admin-Key": "test-admin-key"})
        create_response = await client.post(
            "/v1/keys",
            headers={"X-Admin-Key": "test-admin-key"},
            json={"name": "verification", "tier": "free", "monthly_budget_usd": 0.01, "allowed_models": ["qwen-plus"]},
        )
        revoke_response = await client.delete(
            "/v1/keys/key_test_1", headers={"X-Admin-Key": "test-admin-key"}
        )

    assert list_response.status_code == 200
    assert create_response.status_code == 200
    assert revoke_response.status_code == 200
    for route in (list_route, create_route, revoke_route):
        assert route.called
        assert route.calls[0].request.headers["x-internal-service-key"] == "test-internal-service-key"


@pytest.mark.asyncio
@respx.mock
async def test_key_lifecycle_routes_reject_missing_admin_key_at_http_boundary() -> None:
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://gateway") as client:
        response = await client.get("/v1/keys")

    assert response.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_key_revocation_preserves_not_found_at_http_boundary() -> None:
    upstream = respx.delete("http://auth:8001/internal/keys/key_missing").mock(
        return_value=httpx.Response(404, json={"detail": "API key not found"})
    )
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://gateway") as client:
        response = await client.delete(
            "/v1/keys/key_missing", headers={"X-Admin-Key": "test-admin-key"}
        )

    assert upstream.called
    assert response.status_code == 404
