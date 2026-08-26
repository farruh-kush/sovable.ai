from __future__ import annotations

import json

import pytest
import respx
from fastapi import Request
from gateway.api.auth import activation_start, me, register_start
from httpx import Response


def make_request(method: str, path: str, body: dict | None = None) -> Request:
    payload = json.dumps(body or {}).encode()
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": payload, "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(b"content-type", b"application/json"), (b"user-agent", b"contract-test")],
        "client": ("127.0.0.1", 1000),
        "server": ("gateway", 8000),
        "scheme": "http",
    }
    return Request(scope, receive)


@pytest.mark.asyncio
@respx.mock
async def test_gateway_activation_proxy_preserves_contract() -> None:
    route = respx.post("http://auth:8001/auth/email/activation/start").mock(
        return_value=Response(202, json={"status": "accepted", "expires_in": 3600})
    )
    result = await activation_start(
        make_request("POST", "/auth/email/activation/start", {"email": "user@example.com"})
    )
    assert route.called
    assert result.status_code == 202
    assert json.loads(result.body) == {"status": "accepted", "expires_in": 3600}


@pytest.mark.asyncio
@respx.mock
async def test_gateway_register_proxy_forwards_json_and_error_status() -> None:
    route = respx.post("http://auth:8001/auth/register/email/start").mock(
        return_value=Response(429, json={"error": {"code": "rate_limit_exceeded"}})
    )
    result = await register_start(
        "email",
        make_request("POST", "/auth/register/email/start", {"destination": "user@example.com"}),
    )
    assert route.called
    assert json.loads(route.calls[0].request.content) == {"destination": "user@example.com"}
    assert result.status_code == 429
    assert json.loads(result.body)["error"]["code"] == "rate_limit_exceeded"


@pytest.mark.asyncio
@respx.mock
async def test_gateway_me_proxy_forwards_authorization_compatible_path() -> None:
    route = respx.get("http://auth:8001/auth/me").mock(
        return_value=Response(200, json={"id": "user_1", "role": "user"})
    )
    result = await me(make_request("GET", "/auth/me"))
    assert route.called
    assert result.status_code == 200
