"""OpenAI provider adapter.

Translates the unified schema to the OpenAI API format and normalises
the response back. Supports prompt caching metadata pass-through
(Phase 3 — Task 3.2).

Author: Farruh
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

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

_OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAIAdapter(BaseProviderAdapter):
    """Adapter for the OpenAI API."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None,
        timeout_seconds: float = 30.0,
        base_url: str = _OPENAI_BASE_URL,
    ) -> None:
        super().__init__(api_key, timeout_seconds)
        self._base_url = base_url.rstrip("/")

    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key:
            return self._mock_chat(request)

        payload = {
            "model": request.model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.response_format:
            payload["response_format"] = request.response_format

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

        if response.status_code >= 400:
            raise ProviderError(
                f"OpenAI API error: {response.text}",
                provider=self.name,
                retriable=response.status_code >= 500,
            )

        data = response.json()
        choice = data["choices"][0]
        raw_usage = data.get("usage", {})

        # Phase 3 — Task 3.2: Extract cached token metadata
        cached_tokens = raw_usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)

        usage = UsageInfo(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
            cached_tokens=cached_tokens,
        )

        return ChatCompletionResponse(
            id=data["id"],
            created=data["created"],
            model=data["model"],
            provider=self.name,
            choices=[
                ChatChoice(
                    index=choice["index"],
                    message=ChatMessage(
                        role=choice["message"]["role"],
                        content=choice["message"]["content"],
                    ),
                    finish_reason=choice.get("finish_reason"),
                )
            ],
            usage=usage,
        )

    async def _chat_stream_impl(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        if not self.api_key:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        payload = {
            "model": request.model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json

                        data = json.loads(line[6:])
                        choice = data["choices"][0]
                        yield ChatCompletionChunk(
                            id=data["id"],
                            created=data["created"],
                            model=data["model"],
                            provider=self.name,
                            choices=[
                                ChatCompletionChunkChoice(
                                    index=choice["index"],
                                    delta=ChatCompletionChunkDelta(
                                        role=choice["delta"].get("role"),
                                        content=choice["delta"].get("content"),
                                    ),
                                    finish_reason=choice.get("finish_reason"),
                                )
                            ],
                        )

    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self.api_key:
            return self._mock_embedding(request)

        inputs = request.input if isinstance(request.input, list) else [request.input]
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                json={"model": request.model, "input": inputs},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()

        data = response.json()
        raw_usage = data.get("usage", {})
        usage = UsageInfo(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
        )
        return EmbeddingResponse(
            data=[
                EmbeddingVector(index=item["index"], embedding=item["embedding"])
                for item in data["data"]
            ],
            model=data["model"],
            provider=self.name,
            usage=usage,
        )

    # ── Mock Responses (no API key configured) ───────────────────────────────

    def _mock_chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        content = f"[OpenAI mock] Response to: {request.messages[-1].content}"
        usage = UsageInfo(prompt_tokens=10, completion_tokens=15, total_tokens=25)
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            provider=self.name,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            usage=usage,
        )

    async def _mock_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        words = f"[OpenAI mock stream] {request.messages[-1].content}".split()
        for word in words:
            yield ChatCompletionChunk(
                id=f"chatcmpl-{uuid.uuid4().hex}",
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
                EmbeddingVector(index=i, embedding=[0.1, 0.2, 0.3, 0.4])
                for i, _ in enumerate(items)
            ],
            model=request.model,
            provider=self.name,
            usage=usage,
        )
