"""Provider service tests — Google Gemini adapter.

Tests cover:
- Mock mode (no API key): chat, streaming, embeddings
- Live API mode (mocked with respx): chat, streaming, embeddings,
  error handling, finish-reason mapping, system-instruction handling
- Registry: Google adapter is registered and retrievable

Author: Farruh
"""
from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from ai_routing_shared.models import (
    ChatCompletionRequest,
    ChatMessage,
    EmbeddingRequest,
)
from provider.adapters.google_adapter import GoogleAdapter
from provider.core.config import ProviderSettings
from provider.core.registry import ProviderRegistry


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def adapter_no_key() -> GoogleAdapter:
    """Google adapter with no API key — returns mock responses."""
    return GoogleAdapter(api_key=None)


@pytest.fixture
def adapter_with_key() -> GoogleAdapter:
    """Google adapter with a fake API key — real HTTP calls are mocked by respx."""
    return GoogleAdapter(api_key="fake-google-key-123")


@pytest.fixture
def simple_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="gemini-1.5-flash",
        messages=[ChatMessage(role="user", content="Hello, Gemini!")],
    )


@pytest.fixture
def system_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="gemini-1.5-flash",
        messages=[
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="What is 2+2?"),
        ],
    )


@pytest.fixture
def embedding_request() -> EmbeddingRequest:
    return EmbeddingRequest(model="text-embedding-004", input=["Hello world", "AI routing"])


# ── Mock Mode Tests (no API key) ──────────────────────────────────────────────


class TestGoogleAdapterMockMode:
    """Tests that run without any real or mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_mock_chat_returns_response(
        self, adapter_no_key: GoogleAdapter, simple_request: ChatCompletionRequest
    ) -> None:
        response = await adapter_no_key.chat(simple_request)
        assert response.provider == "google"
        assert response.model == "gemini-1.5-flash"
        assert len(response.choices) == 1
        assert "Google Gemini mock" in response.choices[0].message.content
        assert response.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_mock_stream_yields_chunks(
        self, adapter_no_key: GoogleAdapter, simple_request: ChatCompletionRequest
    ) -> None:
        chunks = []
        async for chunk in adapter_no_key.chat_stream(simple_request):
            chunks.append(chunk)
        assert len(chunks) > 0
        assert all(c.provider == "google" for c in chunks)
        # Last chunk should have finish_reason="stop"
        assert chunks[-1].choices[0].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_mock_embedding_returns_vectors(
        self, adapter_no_key: GoogleAdapter, embedding_request: EmbeddingRequest
    ) -> None:
        response = await adapter_no_key.embeddings(embedding_request)
        assert response.provider == "google"
        assert len(response.data) == 2
        assert response.data[0].index == 0
        assert response.data[1].index == 1
        assert len(response.data[0].embedding) == 4

    @pytest.mark.asyncio
    async def test_mock_chat_with_system_message(
        self, adapter_no_key: GoogleAdapter, system_request: ChatCompletionRequest
    ) -> None:
        response = await adapter_no_key.chat(system_request)
        assert response.provider == "google"
        assert len(response.choices) == 1


# ── Live API Mode Tests (HTTP mocked with respx) ──────────────────────────────


_FAKE_GENERATE_RESPONSE = {
    "candidates": [
        {
            "content": {"parts": [{"text": "4"}], "role": "model"},
            "finishReason": "STOP",
            "index": 0,
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 12,
        "candidatesTokenCount": 1,
        "totalTokenCount": 13,
    },
}

_FAKE_EMBEDDING_RESPONSE = {
    "embedding": {"values": [0.01, 0.02, 0.03, 0.04, 0.05]}
}


class TestGoogleAdapterLiveMode:
    """Tests that mock the Gemini HTTP API using respx."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_success(
        self, adapter_with_key: GoogleAdapter, simple_request: ChatCompletionRequest
    ) -> None:
        respx.post(
            url__regex=r"generativelanguage\.googleapis\.com.*generateContent"
        ).mock(return_value=Response(200, json=_FAKE_GENERATE_RESPONSE))

        response = await adapter_with_key.chat(simple_request)

        assert response.provider == "google"
        assert response.choices[0].message.content == "4"
        assert response.choices[0].finish_reason == "stop"
        assert response.usage.prompt_tokens == 12
        assert response.usage.completion_tokens == 1
        assert response.usage.total_tokens == 13

    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_with_system_instruction(
        self, adapter_with_key: GoogleAdapter, system_request: ChatCompletionRequest
    ) -> None:
        route = respx.post(
            url__regex=r"generativelanguage\.googleapis\.com.*generateContent"
        ).mock(return_value=Response(200, json=_FAKE_GENERATE_RESPONSE))

        response = await adapter_with_key.chat(system_request)

        # Verify systemInstruction was sent in the payload
        sent_payload = json.loads(route.calls[0].request.content)
        assert "systemInstruction" in sent_payload
        assert (
            "You are a helpful assistant"
            in sent_payload["systemInstruction"]["parts"][0]["text"]
        )
        assert response.choices[0].message.content == "4"

    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_429_raises_retriable_error(
        self, adapter_with_key: GoogleAdapter, simple_request: ChatCompletionRequest
    ) -> None:
        from ai_routing_shared.exceptions import ProviderError

        respx.post(
            url__regex=r"generativelanguage\.googleapis\.com.*generateContent"
        ).mock(return_value=Response(429, json={"error": {"message": "quota exceeded"}}))

        with pytest.raises(ProviderError) as exc_info:
            await adapter_with_key._chat_impl(simple_request)

        assert exc_info.value.retriable is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_400_raises_non_retriable_error(
        self, adapter_with_key: GoogleAdapter, simple_request: ChatCompletionRequest
    ) -> None:
        from ai_routing_shared.exceptions import ProviderError

        respx.post(
            url__regex=r"generativelanguage\.googleapis\.com.*generateContent"
        ).mock(return_value=Response(400, json={"error": {"message": "invalid request"}}))

        with pytest.raises(ProviderError) as exc_info:
            await adapter_with_key._chat_impl(simple_request)

        assert exc_info.value.retriable is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_embedding_success(
        self, adapter_with_key: GoogleAdapter, embedding_request: EmbeddingRequest
    ) -> None:
        respx.post(
            url__regex=r"generativelanguage\.googleapis\.com.*embedContent"
        ).mock(return_value=Response(200, json=_FAKE_EMBEDDING_RESPONSE))

        response = await adapter_with_key.embeddings(embedding_request)

        assert response.provider == "google"
        assert len(response.data) == 2
        assert response.data[0].embedding == [0.01, 0.02, 0.03, 0.04, 0.05]


# ── Finish Reason Mapping ─────────────────────────────────────────────────────


class TestFinishReasonMapping:
    def test_stop_maps_to_stop(self) -> None:
        assert GoogleAdapter._map_finish_reason("STOP") == "stop"

    def test_max_tokens_maps_to_length(self) -> None:
        assert GoogleAdapter._map_finish_reason("MAX_TOKENS") == "length"

    def test_safety_maps_to_content_filter(self) -> None:
        assert GoogleAdapter._map_finish_reason("SAFETY") == "content_filter"

    def test_recitation_maps_to_content_filter(self) -> None:
        assert GoogleAdapter._map_finish_reason("RECITATION") == "content_filter"

    def test_unknown_maps_to_stop(self) -> None:
        assert GoogleAdapter._map_finish_reason("UNKNOWN_REASON") == "stop"


# ── Model Alias Resolution ────────────────────────────────────────────────────


class TestModelAliasResolution:
    def test_gemini_pro_alias(self) -> None:
        assert GoogleAdapter._resolve_model("gemini-pro") == "gemini-1.0-pro"

    def test_gemini_flash_alias(self) -> None:
        assert GoogleAdapter._resolve_model("gemini-flash") == "gemini-1.5-flash"

    def test_unknown_model_passes_through(self) -> None:
        assert GoogleAdapter._resolve_model("gemini-2.5-pro") == "gemini-2.5-pro"


# ── Registry Integration ──────────────────────────────────────────────────────


class TestProviderRegistry:
    def test_google_adapter_registered(self) -> None:
        settings = ProviderSettings()
        registry = ProviderRegistry(settings)
        adapter = registry.get("google")
        assert adapter is not None
        assert adapter.name == "google"

    def test_all_four_providers_registered(self) -> None:
        settings = ProviderSettings()
        registry = ProviderRegistry(settings)
        providers = list(registry.all().keys())
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers
        assert "mistral" in providers

    def test_unknown_provider_raises(self) -> None:
        from ai_routing_shared.exceptions import NoProvidersAvailableError

        settings = ProviderSettings()
        registry = ProviderRegistry(settings)
        with pytest.raises(NoProvidersAvailableError):
            registry.get("nonexistent-provider")


class TestMistralAdapter:
    def test_mistral_adapter_registered(self) -> None:
        settings = ProviderSettings()
        registry = ProviderRegistry(settings)
        adapter = registry.get("mistral")
        assert adapter.name == "mistral"
        assert adapter._base_url == "https://api.mistral.ai/v1"

    @pytest.mark.asyncio
    async def test_mistral_mock_chat(self) -> None:
        from provider.adapters.mistral_adapter import MistralAdapter
        adapter = MistralAdapter(api_key=None)
        request = ChatCompletionRequest(
            model="mistral-small-latest",
            messages=[ChatMessage(role="user", content="Hello")],
        )
        response = await adapter.chat(request)
        assert response.provider == "mistral"
        assert response.choices[0].message.role == "assistant"
