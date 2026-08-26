from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
import respx
from ai_routing_shared.exceptions import ModelNotAllowedError, UpstreamServiceError
from ai_routing_shared.models import ApiKey, ChatCompletionRequest, ChatMessage, ProviderPreferences
from fastapi import FastAPI

from gateway.api.v1.chat import _compute_cache_key
from gateway.core.auth import enforce_model_whitelist
from gateway.core.downstream import response_error_or_none
from gateway.main import create_app


class FakeRedis:
    def __init__(self, *, spend: float = 0.0, rate_limit: bool = True) -> None:
        self.spend = spend
        self.rate_limit = rate_limit
        self.rate_calls: list[tuple[str, int, int]] = []
        self.cache: dict[str, str] = {}

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        self.rate_calls.append((key, limit, window_seconds))
        return self.rate_limit

    async def get_monthly_spend(self, api_key_id: str) -> float:
        return self.spend

    async def get_cached_response(self, cache_key: str) -> str | None:
        return self.cache.get(cache_key)

    async def set_cached_response(self, cache_key: str, response: str, ttl_seconds: int = 3600) -> None:
        self.cache[cache_key] = response


def principal(**overrides: Any) -> ApiKey:
    values: dict[str, Any] = {
        "id": "key_1",
        "user_id": "user_1",
        "requests_per_minute": 60,
        "requests_per_day": 2000,
        "allowed_models": ["gpt-4o-mini"],
    }
    values.update(overrides)
    return ApiKey(**values)


def auth_route(api_key: ApiKey | None = None) -> respx.Route:
    return respx.post("http://auth:8001/internal/validate-key").mock(
        return_value=httpx.Response(200, json=(api_key or principal()).model_dump(mode="json"))
    )


def completion_payload() -> dict[str, Any]:
    return {
        "id": "chatcmpl_1",
        "object": "chat.completion",
        "created": 1720000000,
        "model": "gpt-4o-mini",
        "provider": "openai",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 3,
            "completion_tokens": 1,
            "total_tokens": 4,
            "estimated_cost_usd": 0.0001,
        },
        "generation_id": "gen_1",
    }


@pytest.fixture
def app() -> FastAPI:
    application = create_app()
    application.state.redis = FakeRedis()
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as test_client:
        yield test_client


def request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hello")]
    )


def test_cache_key_is_deterministic_and_changes_with_prompt() -> None:
    first = _compute_cache_key(request())
    second = _compute_cache_key(request())
    changed = _compute_cache_key(
        request().model_copy(update={"messages": [ChatMessage(role="user", content="different")]})
    )
    assert first == second
    assert first != changed


def test_cache_key_includes_routing_and_metadata_preferences() -> None:
    base = request()
    changed_provider = base.model_copy(update={"provider": ProviderPreferences(sort="latency")})
    changed_metadata = base.model_copy(update={"metadata": {"tenant": "other"}})
    assert _compute_cache_key(base) != _compute_cache_key(changed_provider)
    assert _compute_cache_key(base) != _compute_cache_key(changed_metadata)


def test_upstream_error_mapping_hides_5xx_body_and_keeps_4xx_detail() -> None:
    with pytest.raises(UpstreamServiceError) as caught:
        response_error_or_none(httpx.Response(500, text="secret stack trace"), "router")
    assert "secret stack trace" not in str(caught.value)

    response = response_error_or_none(
        httpx.Response(400, json={"detail": "invalid request", "secret": "do-not-leak"}),
        "router",
    )
    assert response is not None
    assert response.status_code == 400
    assert response.body == b'{"error":{"code":"upstream_rejected","message":"invalid request"}}'


def test_model_whitelist_allows_configured_model() -> None:
    enforce_model_whitelist("gpt-4o-mini", principal())


def test_model_whitelist_rejects_unconfigured_model() -> None:
    with pytest.raises(ModelNotAllowedError):
        enforce_model_whitelist("gpt-4o", principal())


@pytest.mark.asyncio
@respx.mock
async def test_chat_contract_forwards_principal_and_request_id(client: httpx.AsyncClient) -> None:
    auth = auth_route()
    router = respx.post("http://router:8002/route/chat/completions").mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-test-secret", "X-Request-Id": "req-123"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-123"
    assert response.headers["x-generation-id"] == "gen_1"
    assert auth.called and router.called
    assert json.loads(auth.calls.last.request.content)["raw_key"] == "sk-test-secret"
    forwarded = json.loads(router.calls.last.request.content)
    assert forwarded["_api_key_id"] == "key_1"
    assert forwarded["_user_id"] == "user_1"
    assert router.calls.last.request.headers["x-request-id"] == "req-123"


@pytest.mark.asyncio
@respx.mock
async def test_missing_key_uses_standard_error_envelope(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "authentication_error",
            "message": "Missing API key. Provide it via 'Authorization: Bearer <key>'.",
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_conflicting_api_key_headers_are_rejected_without_auth_call(client: httpx.AsyncClient) -> None:
    auth = auth_route()
    response = await client.get(
        "/v1/models",
        headers={"Authorization": "Bearer first", "X-Api-Key": "second"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"
    assert not auth.called


@pytest.mark.asyncio
@respx.mock
async def test_invalid_request_is_rejected_before_router(client: httpx.AsyncClient) -> None:
    auth_route()
    router = respx.post("http://router:8002/route/chat/completions").mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    response = await client.post(
        "/v1/chat/completions",
        headers={"X-Api-Key": "sk-test"},
        json={"model": "", "messages": []},
    )
    assert response.status_code == 422
    assert not router.called


@pytest.mark.asyncio
@respx.mock
async def test_router_4xx_is_mapped_without_echoing_arbitrary_body(client: httpx.AsyncClient) -> None:
    auth_route()
    respx.post("http://router:8002/route/chat/completions").mock(
        return_value=httpx.Response(400, json={"detail": "bad request", "secret": "do-not-leak"})
    )
    response = await client.post(
        "/v1/chat/completions",
        headers={"X-Api-Key": "sk-test"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "upstream_rejected", "message": "bad request"}}
    assert "do-not-leak" not in response.text


@pytest.mark.asyncio
@respx.mock
async def test_router_5xx_becomes_safe_502(client: httpx.AsyncClient) -> None:
    auth_route()
    respx.post("http://router:8002/route/chat/completions").mock(
        return_value=httpx.Response(503, text="provider secret stack trace")
    )
    response = await client.post(
        "/v1/chat/completions",
        headers={"X-Api-Key": "sk-test"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_service_error"
    assert "provider secret" not in response.text


@pytest.mark.asyncio
@respx.mock
async def test_auth_timeout_is_mapped_to_504(client: httpx.AsyncClient) -> None:
    respx.post("http://auth:8001/internal/validate-key").mock(
        side_effect=httpx.ReadTimeout("auth timed out")
    )
    response = await client.get("/v1/models", headers={"X-Api-Key": "sk-test"})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "upstream_timeout"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_exhaustion_blocks_router(client: httpx.AsyncClient, app: FastAPI) -> None:
    app.state.redis = FakeRedis(rate_limit=False)
    auth_route(principal(requests_per_minute=1))
    router = respx.post("http://router:8002/route/chat/completions").mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    response = await client.post(
        "/v1/chat/completions",
        headers={"X-Api-Key": "sk-test"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"
    assert not router.called


@pytest.mark.asyncio
@respx.mock
async def test_monthly_quota_exhaustion_blocks_router(client: httpx.AsyncClient, app: FastAPI) -> None:
    app.state.redis = FakeRedis(spend=10.0)
    auth_route(principal(monthly_budget_usd=10.0))
    router = respx.post("http://router:8002/route/chat/completions").mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    response = await client.post(
        "/v1/chat/completions",
        headers={"X-Api-Key": "sk-test"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "monthly_budget_exceeded"
    assert not router.called


@pytest.mark.asyncio
@respx.mock
async def test_streaming_sse_is_forwarded_and_not_cached(client: httpx.AsyncClient, app: FastAPI) -> None:
    auth_route()
    stream = respx.post("http://router:8002/route/chat/completions").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"id":"chunk_1"}\n\ndata: [DONE]\n\n',
        )
    )
    response = await client.post(
        "/v1/chat/completions",
        headers={"X-Api-Key": "sk-test"},
        json={
            "model": "gpt-4o-mini",
            "stream": True,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: [DONE]" in response.text
    assert stream.called
    assert app.state.redis.cache == {}


@pytest.mark.asyncio
@respx.mock
async def test_activation_start_forwards_payload_and_response(client: httpx.AsyncClient) -> None:
    activation = respx.post("http://auth:8001/auth/email/activation/start").mock(
        return_value=httpx.Response(
            202,
            json={"status": "sent", "delivery": "email", "expires_in": 600},
        )
    )
    response = await client.post(
        "/auth/email/activation/start",
        headers={"X-Request-Id": "activation-1"},
        json={"email": "person@example.com"},
    )
    assert response.status_code == 202
    assert response.json() == {"status": "sent", "delivery": "email", "expires_in": 600}
    assert json.loads(activation.calls.last.request.content) == {"email": "person@example.com"}
    assert activation.calls.last.request.headers["x-request-id"] == "activation-1"


@pytest.mark.asyncio
@respx.mock
async def test_privacy_preview_forwards_principal_and_never_requires_raw_key_at_router(
    client: httpx.AsyncClient,
) -> None:
    auth_route()
    preview = respx.post("http://router:8002/route/privacy/preview").mock(
        return_value=httpx.Response(
            200,
            json={"messages": [{"role": "user", "content": "<EMAIL_1>"}], "token_count": 1},
        )
    )
    response = await client.post(
        "/v1/privacy/preview",
        headers={"X-Api-Key": "sk-test"},
        json={"messages": [{"role": "user", "content": "person@example.com"}]},
    )
    assert response.status_code == 200
    assert response.json()["messages"][0]["content"] == "<EMAIL_1>"
    forwarded = json.loads(preview.calls.last.request.content)
    assert forwarded["_api_key_id"] == "key_1"
    assert "sk-test" not in json.dumps(forwarded)
