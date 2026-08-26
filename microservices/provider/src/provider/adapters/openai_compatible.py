"""OpenAI-compatible provider adapter implementation."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator, Optional

from ai_routing_shared.exceptions import ProviderError
from ai_routing_shared.models import (
    ChatChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingVector,
    UsageInfo,
)

from ..contracts import Capability, CapabilitySet, ProviderMetadata, UsageSource
from .base import BaseProviderAdapter


class OpenAICompatibleAdapter(BaseProviderAdapter):
    """Adapter for APIs that expose OpenAI chat and embedding shapes."""

    allowed_hosts = frozenset()

    def __init__(self, api_key: Optional[str], timeout_seconds: float = 30.0, *, base_url: str, mock_mode: bool = True, **kwargs: Any) -> None:
        super().__init__(api_key, timeout_seconds, base_url=base_url, mock_mode=mock_mode, **kwargs)

    @property
    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(
            provider=self.name,
            configured=self.configured,
            capabilities={Capability.CHAT, Capability.STREAMING, Capability.EMBEDDINGS, Capability.SYSTEM_MESSAGES, Capability.JSON_MODE, Capability.TOOLS},
        )

    def _headers(self, *, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def _payload(request: ChatCompletionRequest, *, stream: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
            "stream": stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.response_format is not None:
            payload["response_format"] = request.response_format
        return payload

    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key and self.mock_mode:
            return self._mock_chat(request)
        if not self.api_key:
            raise self._error_from_missing_secret()
        client = await self._get_client()
        response = await client.post(f"{self._base_url}/chat/completions", json=self._payload(request), headers=self._headers(idempotency_key=str(uuid.uuid4())))
        self._raise_for_response(response)
        data = self._json(response, self.name)
        try:
            raw_choice = data["choices"][0]
            message = raw_choice.get("message", {})
            content = message.get("content", "")
            usage_raw = data.get("usage") or {}
            prompt_tokens = int(usage_raw.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage_raw.get("completion_tokens", 0) or 0)
            total_tokens = int(usage_raw.get("total_tokens", prompt_tokens + completion_tokens) or 0)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Provider returned malformed chat response.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc
        return ChatCompletionResponse(
            id=str(data.get("id") or f"chatcmpl-{uuid.uuid4().hex}"),
            created=int(data.get("created") or time.time()),
            model=str(data.get("model") or request.model),
            provider=self.name,
            choices=[ChatChoice(index=int(raw_choice.get("index", 0)), message=ChatMessage(role=str(message.get("role", "assistant")), content=content), finish_reason=self._map_finish_reason(raw_choice.get("finish_reason")))],
            usage=UsageInfo(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens),
        )

    async def _chat_stream_impl(self, request: ChatCompletionRequest) -> AsyncIterator[ChatCompletionChunk]:
        if not self.api_key and self.mock_mode:
            async for chunk in self._mock_stream(request):
                yield chunk
            return
        if not self.api_key:
            raise self._error_from_missing_secret()
        client = await self._get_client()
        async with client.stream("POST", f"{self._base_url}/chat/completions", json=self._payload(request, stream=True), headers=self._headers(idempotency_key=str(uuid.uuid4()))) as response:
            self._raise_for_response(response)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                try:
                    data = json.loads(raw)
                    choice = (data.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    yield ChatCompletionChunk(
                        id=str(data.get("id") or f"chatcmpl-{uuid.uuid4().hex}"),
                        created=int(data.get("created") or time.time()),
                        model=str(data.get("model") or request.model),
                        provider=self.name,
                        choices=[ChatCompletionChunkChoice(index=int(choice.get("index", 0)), delta=ChatCompletionChunkDelta(role=delta.get("role"), content=delta.get("content")), finish_reason=self._map_finish_reason(choice.get("finish_reason")))],
                    )
                except (ValueError, TypeError, KeyError, IndexError) as exc:
                    raise ProviderError("Provider returned malformed stream data.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc

    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self.api_key and self.mock_mode:
            return self._mock_embedding(request)
        if not self.api_key:
            raise self._error_from_missing_secret()
        inputs = request.input if isinstance(request.input, list) else [request.input]
        client = await self._get_client()
        response = await client.post(f"{self._base_url}/embeddings", json={"model": request.model, "input": inputs}, headers=self._headers(idempotency_key=str(uuid.uuid4())))
        self._raise_for_response(response)
        data = self._json(response, self.name)
        try:
            vectors = [EmbeddingVector(index=int(item.get("index", i)), embedding=[float(x) for x in item["embedding"]]) for i, item in enumerate(data["data"])]
            usage_raw = data.get("usage") or {}
            usage = UsageInfo(prompt_tokens=int(usage_raw.get("prompt_tokens", 0) or 0), total_tokens=int(usage_raw.get("total_tokens", 0) or 0))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("Provider returned malformed embedding response.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc
        return EmbeddingResponse(data=vectors, model=str(data.get("model") or request.model), provider=self.name, usage=usage)

    @staticmethod
    def _map_finish_reason(reason: Any) -> str | None:
        if reason is None:
            return None
        return {"stop": "stop", "length": "length", "content_filter": "content_filter", "tool_calls": "tool_calls"}.get(str(reason), "stop")

    def _error_from_missing_secret(self) -> ProviderError:
        return self._error_from_classification("authentication", "Provider authentication is not configured.", retryable=False)

    def _error_from_classification(self, classification: str, message: str, *, retryable: bool) -> ProviderError:
        from ..contracts import ErrorClass
        return self._error(ErrorClass(classification), message, retryable=retryable)

    def _mock_chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return ChatCompletionResponse(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatChoice(index=0, message=ChatMessage(role="assistant", content=f"[{self.name} mock] response"), finish_reason="stop")], usage=UsageInfo(prompt_tokens=1, completion_tokens=1, total_tokens=2))

    async def _mock_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatCompletionChunk]:
        yield ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatCompletionChunkChoice(index=0, delta=ChatCompletionChunkDelta(role="assistant"), finish_reason=None)])
        yield ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatCompletionChunkChoice(index=0, delta=ChatCompletionChunkDelta(content=f"[{self.name} mock] response"), finish_reason="stop")])

    def _mock_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        items = request.input if isinstance(request.input, list) else [request.input]
        return EmbeddingResponse(data=[EmbeddingVector(index=i, embedding=[0.0, 0.0, 0.0, 0.0]) for i, _ in enumerate(items)], model=request.model, provider=self.name, usage=UsageInfo(prompt_tokens=len(items), total_tokens=len(items)))
