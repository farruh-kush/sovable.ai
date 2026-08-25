"""Google Gemini provider adapter.

Translates the unified schema to the Google Generative Language API
(``generativelanguage.googleapis.com``).

Supports:
- Chat completions via ``generateContent``
- Streaming via ``streamGenerateContent``
- Embeddings via ``embedContent``

The adapter maps the OpenAI-compatible role names (``user``, ``assistant``,
``system``) to Gemini's role names (``user``, ``model``) and inlines any
system message as the first ``user`` turn, which is the recommended pattern
for Gemini models that do not have a dedicated system instruction field.

For Gemini 1.5+ models the adapter uses the ``systemInstruction`` field when
a system message is present, which is the preferred approach.

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

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Gemini models that support the systemInstruction field (1.5+)
_SYSTEM_INSTRUCTION_MODELS = {
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
}

# Default embedding model
_DEFAULT_EMBEDDING_MODEL = "text-embedding-004"


class GoogleAdapter(BaseProviderAdapter):
    """Adapter for the Google Generative Language (Gemini) API."""

    name = "google"

    def __init__(self, api_key: str | None, timeout_seconds: float = 30.0) -> None:
        super().__init__(api_key, timeout_seconds)

    # ── Chat Completion ───────────────────────────────────────────────────────

    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key:
            return self._mock_chat(request)

        payload = self._build_generate_payload(request)
        model_id = self._resolve_model(request.model)
        url = f"{_GEMINI_BASE_URL}/models/{model_id}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, json=payload)

        if response.status_code != 200:
            raise ProviderError(
                f"Google API error {response.status_code}: {response.text}",
                provider=self.name,
                retriable=response.status_code in {429, 500, 502, 503},
            )

        data = response.json()
        return self._parse_generate_response(data, request.model)

    async def _chat_stream_impl(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        if not self.api_key:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        payload = self._build_generate_payload(request)
        model_id = self._resolve_model(request.model)
        url = (
            f"{_GEMINI_BASE_URL}/models/{model_id}:streamGenerateContent?alt=sse&key={self.api_key}"
        )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    raise ProviderError(
                        f"Google streaming API error {response.status_code}",
                        provider=self.name,
                        retriable=response.status_code in {429, 500, 502, 503},
                    )
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json as _json

                        try:
                            data = _json.loads(line[6:])
                        except ValueError:
                            continue
                        chunk = self._parse_stream_chunk(data, request.model)
                        if chunk:
                            yield chunk

    # ── Embeddings ────────────────────────────────────────────────────────────

    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self.api_key:
            return self._mock_embedding(request)

        inputs = request.input if isinstance(request.input, list) else [request.input]
        model_id = self._resolve_model(
            request.model if request.model != "text-embedding-ada-002" else _DEFAULT_EMBEDDING_MODEL
        )

        embeddings: list[EmbeddingVector] = []
        total_tokens = 0

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for idx, text in enumerate(inputs):
                url = f"{_GEMINI_BASE_URL}/models/{model_id}:embedContent?key={self.api_key}"
                payload = {
                    "model": f"models/{model_id}",
                    "content": {"parts": [{"text": text}]},
                }
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise ProviderError(
                        f"Google Embeddings API error {response.status_code}: {response.text}",
                        provider=self.name,
                        retriable=response.status_code in {429, 500, 502, 503},
                    )
                data = response.json()
                vector = data.get("embedding", {}).get("values", [])
                embeddings.append(EmbeddingVector(index=idx, embedding=vector))
                # Gemini does not return token counts for embeddings; estimate
                total_tokens += max(1, len(text.split()))

        usage = UsageInfo(prompt_tokens=total_tokens, total_tokens=total_tokens)
        return EmbeddingResponse(
            data=embeddings,
            model=request.model,
            provider=self.name,
            usage=usage,
        )

    # ── Payload Builders ──────────────────────────────────────────────────────

    def _build_generate_payload(self, request: ChatCompletionRequest) -> dict[str, Any]:
        """Build the ``generateContent`` request payload from the unified schema."""
        system_text: str | None = None
        conversation: list[dict[str, Any]] = []

        for msg in request.messages:
            if msg.role == "system":
                # Accumulate system messages into a single instruction string
                text = (
                    msg.content
                    if isinstance(msg.content, str)
                    else " ".join(
                        part.get("text", "") for part in msg.content if isinstance(part, dict)
                    )
                )
                system_text = (system_text + "\n" + text) if system_text else text
            else:
                gemini_role = "user" if msg.role == "user" else "model"
                content_parts: list[dict[str, str]]
                if isinstance(msg.content, str):
                    content_parts = [{"text": msg.content}]
                else:
                    content_parts = [
                        {"text": part.get("text", "")}
                        for part in msg.content
                        if isinstance(part, dict) and "text" in part
                    ]
                conversation.append({"role": gemini_role, "parts": content_parts})

        # If no explicit user/model turns exist, wrap system text as a user turn
        if not conversation and system_text:
            conversation.append({"role": "user", "parts": [{"text": system_text}]})
            system_text = None

        payload: dict[str, Any] = {"contents": conversation}

        # Use systemInstruction for supported models
        if system_text and any(m in request.model for m in _SYSTEM_INSTRUCTION_MODELS):
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        elif system_text:
            # Prepend system text as first user turn for older models
            conversation.insert(0, {"role": "user", "parts": [{"text": system_text}]})

        generation_config: dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if generation_config:
            payload["generationConfig"] = generation_config

        return payload

    def _parse_generate_response(self, data: dict[str, Any], model: str) -> ChatCompletionResponse:
        """Parse a ``generateContent`` response into the unified schema."""
        candidates = data.get("candidates", [])
        choices: list[ChatChoice] = []

        for idx, candidate in enumerate(candidates):
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            text = "".join(part.get("text", "") for part in parts)
            finish_reason_raw = candidate.get("finishReason", "STOP")
            finish_reason = self._map_finish_reason(finish_reason_raw)
            choices.append(
                ChatChoice(
                    index=idx,
                    message=ChatMessage(role="assistant", content=text),
                    finish_reason=finish_reason,
                )
            )

        usage_meta = data.get("usageMetadata", {})
        usage = UsageInfo(
            prompt_tokens=usage_meta.get("promptTokenCount", 0),
            completion_tokens=usage_meta.get("candidatesTokenCount", 0),
            total_tokens=usage_meta.get("totalTokenCount", 0),
        )

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=model,
            provider=self.name,
            choices=choices,
            usage=usage,
        )

    def _parse_stream_chunk(self, data: dict[str, Any], model: str) -> ChatCompletionChunk | None:
        """Parse a single SSE data event from ``streamGenerateContent``."""
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        finish_reason_raw = candidate.get("finishReason")
        finish_reason = self._map_finish_reason(finish_reason_raw) if finish_reason_raw else None

        return ChatCompletionChunk(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=model,
            provider=self.name,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatCompletionChunkDelta(
                        role="assistant" if not text else None,
                        content=text or None,
                    ),
                    finish_reason=finish_reason,
                )
            ],
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_model(model: str) -> str:
        """Map common model aliases to the Gemini API model ID."""
        _aliases: dict[str, str] = {
            # Allow callers to use short names
            "gemini-pro": "gemini-1.0-pro",
            "gemini-flash": "gemini-1.5-flash",
            "gemini-ultra": "gemini-1.0-ultra",
        }
        return _aliases.get(model, model)

    @staticmethod
    def _map_finish_reason(reason: str) -> str:
        """Map Gemini finish reasons to OpenAI-compatible values."""
        _mapping: dict[str, str] = {
            "STOP": "stop",
            "MAX_TOKENS": "length",
            "SAFETY": "content_filter",
            "RECITATION": "content_filter",
            "OTHER": "stop",
            "FINISH_REASON_UNSPECIFIED": "stop",
        }
        return _mapping.get(reason.upper(), "stop")

    # ── Mock Responses (no API key configured) ────────────────────────────────

    def _mock_chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        content = f"[Google Gemini mock] Response to: {request.messages[-1].content}"
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
        words = f"[Google Gemini mock stream] {request.messages[-1].content}".split()
        for i, word in enumerate(words):
            yield ChatCompletionChunk(
                id=f"chatcmpl-{uuid.uuid4().hex}",
                created=int(time.time()),
                model=request.model,
                provider=self.name,
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChatCompletionChunkDelta(
                            content=f"{word} ",
                        ),
                        finish_reason="stop" if i == len(words) - 1 else None,
                    )
                ],
            )

    def _mock_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        items = request.input if isinstance(request.input, list) else [request.input]
        usage = UsageInfo(
            prompt_tokens=len(items) * 5,
            total_tokens=len(items) * 5,
        )
        return EmbeddingResponse(
            data=[
                EmbeddingVector(index=i, embedding=[0.1, 0.2, 0.3, 0.4])
                for i, _ in enumerate(items)
            ],
            model=request.model,
            provider=self.name,
            usage=usage,
        )
