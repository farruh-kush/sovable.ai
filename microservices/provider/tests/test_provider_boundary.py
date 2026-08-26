from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import pytest
import respx
from httpx import Response

from ai_routing_shared.exceptions import NoProvidersAvailableError, ProviderCircuitOpenError, ProviderError
from ai_routing_shared.models import ChatCompletionRequest, ChatMessage, EmbeddingRequest
from provider.adapters.base import BaseProviderAdapter, RetryPolicy
from provider.adapters.openai_adapter import OpenAIAdapter
from provider.adapters.qwen_adapter import AlibabaQwenAdapter
from provider.contracts import Capability, NormalizedRequest, ProviderMetadata, TokenUsage, UsageSource, calculate_cost
from provider.core.config import ProviderSettings
from provider.core.registry import ProviderRegistry


@pytest.fixture
def chat_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(model="qwen-plus", messages=[ChatMessage(role="user", content="hello")])


_QWEN_OK = {
    "id": "qwen-fixture-1",
    "created": 1720000000,
    "model": "qwen-plus",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
}


class TestTypedContracts:
    def test_normalized_request_is_strict_and_typed(self) -> None:
        request = NormalizedRequest(request_id="r1", model="qwen-plus", messages_or_input=[{"role": "user", "content": "x"}], deadline_at=datetime.now(timezone.utc))
        assert request.timeout_ms == 30_000
        assert request.request_id == "r1"

    def test_cost_mapping_is_deterministic(self) -> None:
        metadata = ProviderMetadata(model="qwen-plus", provider="alibaba", input_cost_per_million=0.8, output_cost_per_million=2.0)
        cost = calculate_cost(metadata, TokenUsage(input_tokens=1000, output_tokens=500, total_tokens=1500, source=UsageSource.MEASURED))
        assert cost.amount == pytest.approx(0.0018)
        assert cost.source == "local_price_table"

    def test_unavailable_cost_does_not_invent_price(self) -> None:
        cost = calculate_cost(None, TokenUsage(input_tokens=1, output_tokens=1))
        assert cost.amount == 0
        assert cost.source == "unavailable"


class TestQwenFixtures:
    @pytest.mark.asyncio
    @respx.mock
    async def test_success_normalizes_chat_and_reuses_client(self, chat_request: ChatCompletionRequest) -> None:
        route = respx.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions").mock(return_value=Response(200, json=_QWEN_OK))
        adapter = AlibabaQwenAdapter("fixture-secret", retry_policy=RetryPolicy(max_attempts=1))
        first = await adapter.chat(chat_request)
        second = await adapter.chat(chat_request)
        assert first.provider == "alibaba"
        assert first.choices[0].message.content == "hi"
        assert first.usage.total_tokens == 6
        assert route.call_count == 2
        assert adapter._client is not None
        await adapter.aclose()

    @pytest.mark.asyncio
    @respx.mock
    async def test_quota_is_retryable_and_honors_budget(self, chat_request: ChatCompletionRequest) -> None:
        route = respx.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions").mock(side_effect=[Response(429, headers={"retry-after": "0"}), Response(200, json=_QWEN_OK)])
        adapter = AlibabaQwenAdapter("fixture-secret", retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0, jitter_seconds=0))
        response = await adapter.chat(chat_request)
        assert response.choices[0].message.content == "hi"
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_malformed_response_is_non_retryable(self, chat_request: ChatCompletionRequest) -> None:
        route = respx.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions").mock(return_value=Response(200, text="not-json"))
        adapter = AlibabaQwenAdapter("fixture-secret", retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0, jitter_seconds=0))
        with pytest.raises(ProviderError) as exc_info:
            await adapter.chat(chat_request)
        assert exc_info.value.retriable is False
        assert route.call_count == 1
        assert "fixture-secret" not in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_retries_then_classifies(self, chat_request: ChatCompletionRequest) -> None:
        route = respx.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions").mock(side_effect=httpx.ReadTimeout("fixture timeout"))
        adapter = AlibabaQwenAdapter("fixture-secret", timeout_seconds=0.2, retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0, jitter_seconds=0))
        with pytest.raises(ProviderError) as exc_info:
            await adapter.chat(chat_request)
        assert exc_info.value.retriable is True
        assert exc_info.value.details["classification"] == "timeout"
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_outage_opens_circuit_after_failure_budget(self, chat_request: ChatCompletionRequest) -> None:
        route = respx.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions").mock(return_value=Response(503))
        adapter = AlibabaQwenAdapter("fixture-secret", retry_policy=RetryPolicy(max_attempts=1, base_delay_seconds=0, jitter_seconds=0))
        for _ in range(3):
            with pytest.raises(ProviderError):
                await adapter.chat(chat_request)
        with pytest.raises(ProviderCircuitOpenError):
            await adapter.chat(chat_request)
        assert route.call_count == 3
        assert (await adapter.health_check()).circuit_open is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_embeddings_normalize_batch(self) -> None:
        route = respx.post("https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings").mock(return_value=Response(200, json={"model": "text-embedding-v3", "data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 1, "embedding": [0.3, 0.4]}], "usage": {"prompt_tokens": 4, "total_tokens": 4}}))
        adapter = AlibabaQwenAdapter("fixture-secret", retry_policy=RetryPolicy(max_attempts=1))
        response = await adapter.embeddings(EmbeddingRequest(model="text-embedding-v3", input=["a", "b"]))
        assert [vector.index for vector in response.data] == [0, 1]
        assert response.usage.total_tokens == 4
        assert route.call_count == 1


class FakeAdapter(BaseProviderAdapter):
    name = "fake"

    def __init__(self, outcomes: list[str]) -> None:
        super().__init__("fake-secret", retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0, jitter_seconds=0))
        self.outcomes = outcomes
        self.calls = 0

    async def _chat_impl(self, request: ChatCompletionRequest):
        self.calls += 1
        outcome = self.outcomes.pop(0) if self.outcomes else "ok"
        if outcome == "retry":
            raise self._error_from_fake()
        return OpenAIAdapter(None)._mock_chat(request)

    async def _chat_stream_impl(self, request: ChatCompletionRequest):
        if False:
            yield None

    async def _embedding_impl(self, request: EmbeddingRequest):
        raise NotImplementedError

    def _error_from_fake(self) -> ProviderError:
        from provider.contracts import ErrorClass
        return self._error(ErrorClass.SERVER_ERROR, "fixture failure", retryable=True)


class TestResilienceAndIsolation:
    @pytest.mark.asyncio
    async def test_retry_budget_and_cancellation(self, chat_request: ChatCompletionRequest) -> None:
        adapter = FakeAdapter(["retry", "ok"])
        response = await adapter.chat(chat_request)
        assert response.provider == "openai"
        assert adapter.calls == 2
        task = asyncio.create_task(adapter.chat(chat_request))
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    def test_provider_capabilities_are_explicit(self) -> None:
        assert Capability.STREAMING in AlibabaQwenAdapter("x").capabilities.capabilities
        assert Capability.EMBEDDINGS in AlibabaQwenAdapter("x").capabilities.capabilities
        assert Capability.EMBEDDINGS not in ProviderRegistry(ProviderSettings()).get("anthropic").capabilities.capabilities

    def test_unknown_provider_is_not_selectable(self) -> None:
        with pytest.raises(NoProvidersAvailableError):
            ProviderRegistry(ProviderSettings()).get("unknown-provider")

    def test_ssrf_and_non_https_endpoints_are_rejected(self) -> None:
        with pytest.raises(ValueError):
            OpenAIAdapter("x", base_url="http://127.0.0.1:8000/v1")
        with pytest.raises(ValueError):
            AlibabaQwenAdapter("x", base_url="https://attacker.example/v1")


class TestVersionedHttpContract:
    @pytest.mark.asyncio
    async def test_versioned_chat_stream_and_legacy_embeddings(self) -> None:
        from provider.main import create_app
        app = create_app()
        app.state.registry = ProviderRegistry(ProviderSettings(PROVIDER_MOCK_MODE=True))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://provider.test") as client:
            stream_response = await client.post("/v1/adapt/chat/completions", headers={"X-Correlation-Id": "corr-fixture"}, json={"_provider": "qwen", "model": "qwen-plus", "messages": [{"role": "user", "content": "hello"}], "stream": True})
            assert stream_response.status_code == 200
            assert "text/event-stream" in stream_response.headers["content-type"]
            assert "data: [DONE]" in stream_response.text
            embedding_response = await client.post("/adapt/embeddings", json={"_provider": "qwen", "model": "text-embedding-v3", "input": ["a", "b"]})
            assert embedding_response.status_code == 200
            assert len(embedding_response.json()["data"]) == 2
