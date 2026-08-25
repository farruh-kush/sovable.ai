"""Anthropic provider adapter.

Translates the unified schema to the Anthropic Messages API format.
Implements prompt caching pass-through (Phase 3 — Task 3.2) by
forwarding ``cache_control`` breakpoints in message content and
extracting ``cache_read_input_tokens`` from the response.

Author: Farruh
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
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
from ai_routing_shared.utils import get_logger

from .base import BaseProviderAdapter

logger = get_logger(__name__)

_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(BaseProviderAdapter):
    """Adapter for the Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, api_key: str | None, timeout_seconds: float = 30.0) -> None:
        super().__init__(api_key, timeout_seconds)

    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key:
            return self._mock_chat(request)

        # Separate system messages from conversation messages
        system_parts: list[str | dict] = []
        user_messages = []

        for msg in request.messages:
            if msg.role == "system":
                # Phase 3 — Task 3.2: Preserve cache_control in system messages
                if isinstance(msg.content, list):
                    system_parts.extend(msg.content)
                else:
                    system_parts.append(msg.content)
            else:
                role = "user" if msg.role == "user" else "assistant"
                # Phase 3 — Task 3.2: Preserve cache_control in user messages
                if isinstance(msg.content, list):
                    user_messages.append({"role": role, "content": msg.content})
                else:
                    user_messages.append({"role": role, "content": msg.content})

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": user_messages,
            "max_tokens": request.max_tokens or 1024,
            "temperature": request.temperature,
        }

        if system_parts:
            payload["system"] = system_parts if len(system_parts) > 1 else system_parts[0]

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "anthropic-beta": "prompt-caching-2024-07-31",
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{_ANTHROPIC_BASE_URL}/messages",
                json=payload,
                headers=headers,
            )

        if response.status_code >= 400:
            raise ProviderError(
                f"Anthropic API error: {response.text}",
                provider=self.name,
                retriable=response.status_code >= 500,
            )

        data = response.json()
        text = "".join(block["text"] for block in data["content"] if block.get("type") == "text")
        raw_usage = data.get("usage", {})

        # Phase 3 — Task 3.2: Extract Anthropic cache hit metadata
        cached_tokens = raw_usage.get("cache_read_input_tokens", 0)
        cache_hit = cached_tokens > 0

        usage = UsageInfo(
            prompt_tokens=raw_usage.get("input_tokens", 0),
            completion_tokens=raw_usage.get("output_tokens", 0),
            total_tokens=raw_usage.get("input_tokens", 0) + raw_usage.get("output_tokens", 0),
            cached_tokens=cached_tokens,
            cache_hit=cache_hit,
        )

        return ChatCompletionResponse(
            id=data["id"],
            created=int(time.time()),
            model=request.model,
            provider=self.name,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=text),
                    finish_reason=data.get("stop_reason", "stop"),
                )
            ],
            usage=usage,
            cache_hit=cache_hit,
        )

    async def _chat_stream_impl(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        # Streaming implementation for Anthropic SSE
        if not self.api_key:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        payload = {
            "model": request.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
                if m.role != "system"
            ],
            "max_tokens": request.max_tokens or 1024,
            "stream": True,
        }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{_ANTHROPIC_BASE_URL}/messages",
                json=payload,
                headers=headers,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json

                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError:
                            # Providers can emit keep-alive or partial SSE frames.
                            # Ignore only malformed JSON frames; transport errors must propagate.
                            continue
                        if event.get("type") == "content_block_delta":
                            delta_text = event.get("delta", {}).get("text", "")
                            yield ChatCompletionChunk(
                                id=f"msg-{uuid.uuid4().hex}",
                                created=int(time.time()),
                                model=request.model,
                                provider=self.name,
                                choices=[
                                    ChatCompletionChunkChoice(
                                        index=0,
                                        delta=ChatCompletionChunkDelta(content=delta_text),
                                        finish_reason=None,
                                    )
                                ],
                            )

    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse:
        # Anthropic does not currently offer an embeddings API
        return self._mock_embedding(request)

    def _mock_chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        content = f"[Anthropic mock] Response to: {request.messages[-1].content}"
        usage = UsageInfo(prompt_tokens=12, completion_tokens=18, total_tokens=30)
        return ChatCompletionResponse(
            id=f"msg-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            provider=self.name,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="end_turn",
                )
            ],
            usage=usage,
        )

    async def _mock_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        words = f"[Anthropic mock stream] {request.messages[-1].content}".split()
        for word in words:
            yield ChatCompletionChunk(
                id=f"msg-{uuid.uuid4().hex}",
                created=int(time.time()),
                model=request.model,
                provider=self.name,
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChatCompletionChunkDelta(content=f"{word} "),
                        finish_reason=None,
                    )
                ],
            )

    def _mock_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        items = request.input if isinstance(request.input, list) else [request.input]
        usage = UsageInfo(prompt_tokens=len(items) * 5, total_tokens=len(items) * 5)
        return EmbeddingResponse(
            data=[
                EmbeddingVector(index=i, embedding=[0.2, 0.4, 0.6, 0.8])
                for i, _ in enumerate(items)
            ],
            model=request.model,
            provider=self.name,
            usage=usage,
        )
