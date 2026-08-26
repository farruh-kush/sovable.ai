"""Anthropic Messages API adapter."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator, Optional

from ai_routing_shared.exceptions import ProviderError
from ai_routing_shared.models import ChatChoice, ChatCompletionChunk, ChatCompletionChunkChoice, ChatCompletionChunkDelta, ChatCompletionRequest, ChatCompletionResponse, ChatMessage, EmbeddingRequest, EmbeddingResponse, EmbeddingVector, UsageInfo

from ..contracts import Capability, CapabilitySet
from .base import BaseProviderAdapter

_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(BaseProviderAdapter):
    name = "anthropic"
    default_base_url = _ANTHROPIC_BASE_URL
    allowed_hosts = frozenset({"api.anthropic.com"})

    def __init__(self, api_key: Optional[str], timeout_seconds: float = 30.0, *, mock_mode: bool = True, **kwargs: Any) -> None:
        super().__init__(api_key, timeout_seconds, base_url=_ANTHROPIC_BASE_URL, mock_mode=mock_mode, **kwargs)

    @property
    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(provider=self.name, configured=self.configured, capabilities={Capability.CHAT, Capability.STREAMING, Capability.SYSTEM_MESSAGES})

    def _headers(self, *, stream: bool = False) -> dict[str, str]:
        headers = {"x-api-key": str(self.api_key), "anthropic-version": _ANTHROPIC_VERSION, "content-type": "application/json"}
        if stream:
            headers["accept"] = "text/event-stream"
        return headers

    def _payload(self, request: ChatCompletionRequest, *, stream: bool = False) -> dict[str, Any]:
        system = [message.content for message in request.messages if message.role == "system" and isinstance(message.content, str)]
        messages = [{"role": "user" if message.role == "user" else "assistant", "content": message.content} for message in request.messages if message.role != "system"]
        payload: dict[str, Any] = {"model": request.model, "messages": messages, "max_tokens": request.max_tokens or 1024, "temperature": request.temperature, "stream": stream}
        if system:
            payload["system"] = "\n\n".join(system)
        return payload

    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key and self.mock_mode:
            return self._mock_chat(request)
        if not self.api_key:
            raise self._error_from_missing_secret()
        client = await self._get_client()
        response = await client.post(f"{self._base_url}/messages", json=self._payload(request), headers=self._headers())
        self._raise_for_response(response)
        data = self._json(response, self.name)
        try:
            text = "".join(str(block.get("text", "")) for block in (data.get("content") or []) if block.get("type") == "text")
            usage_raw = data.get("usage") or {}
            input_tokens = int(usage_raw.get("input_tokens", 0) or 0)
            output_tokens = int(usage_raw.get("output_tokens", 0) or 0)
        except (TypeError, ValueError) as exc:
            raise ProviderError("Provider returned malformed chat response.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc
        return ChatCompletionResponse(id=str(data.get("id") or f"chatcmpl-{uuid.uuid4().hex}"), created=int(time.time()), model=str(data.get("model") or request.model), provider=self.name, choices=[ChatChoice(index=0, message=ChatMessage(role="assistant", content=text), finish_reason={"end_turn": "stop", "max_tokens": "length", "stop_sequence": "stop"}.get(str(data.get("stop_reason")), "stop"))], usage=UsageInfo(prompt_tokens=input_tokens, completion_tokens=output_tokens, total_tokens=input_tokens + output_tokens, cached_tokens=int(usage_raw.get("cache_read_input_tokens", 0) or 0)))

    async def _chat_stream_impl(self, request: ChatCompletionRequest) -> AsyncIterator[ChatCompletionChunk]:
        if not self.api_key and self.mock_mode:
            async for chunk in self._mock_stream(request):
                yield chunk
            return
        if not self.api_key:
            raise self._error_from_missing_secret()
        client = await self._get_client()
        async with client.stream("POST", f"{self._base_url}/messages", json=self._payload(request, stream=True), headers=self._headers(stream=True)) as response:
            self._raise_for_response(response)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except ValueError as exc:
                    raise ProviderError("Provider returned malformed stream data.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc
                event = data.get("type")
                if event == "content_block_delta":
                    delta = data.get("delta") or {}
                    yield ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatCompletionChunkChoice(index=0, delta=ChatCompletionChunkDelta(content=delta.get("text")), finish_reason=None)])
                elif event == "message_delta":
                    stop_reason = (data.get("delta") or {}).get("stop_reason")
                    if stop_reason:
                        yield ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatCompletionChunkChoice(index=0, delta=ChatCompletionChunkDelta(), finish_reason={"end_turn": "stop", "max_tokens": "length"}.get(stop_reason, "stop"))])

    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if self.mock_mode and not self.api_key:
            items = request.input if isinstance(request.input, list) else [request.input]
            return EmbeddingResponse(data=[EmbeddingVector(index=i, embedding=[0.0, 0.0, 0.0, 0.0]) for i, _ in enumerate(items)], model=request.model, provider=self.name, usage=UsageInfo())
        raise self._error_from_missing_secret()

    def _error_from_missing_secret(self) -> ProviderError:
        from ..contracts import ErrorClass
        return self._error(ErrorClass.AUTHENTICATION, "Provider authentication is not configured.", retryable=False)

    def _mock_chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return ChatCompletionResponse(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatChoice(index=0, message=ChatMessage(role="assistant", content="[Anthropic mock] response"), finish_reason="stop")], usage=UsageInfo(prompt_tokens=1, completion_tokens=1, total_tokens=2))

    async def _mock_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatCompletionChunk]:
        yield ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatCompletionChunkChoice(index=0, delta=ChatCompletionChunkDelta(content="[Anthropic mock] response"), finish_reason="stop")])
