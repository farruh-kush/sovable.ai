"""Google Gemini provider adapter."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from ai_routing_shared.exceptions import ProviderError
from ai_routing_shared.models import ChatChoice, ChatCompletionChunk, ChatCompletionChunkChoice, ChatCompletionChunkDelta, ChatCompletionRequest, ChatCompletionResponse, ChatMessage, EmbeddingRequest, EmbeddingResponse, EmbeddingVector, UsageInfo

from ..contracts import Capability, CapabilitySet
from .base import BaseProviderAdapter

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GoogleAdapter(BaseProviderAdapter):
    name = "google"
    default_base_url = _GEMINI_BASE_URL
    allowed_hosts = frozenset({"generativelanguage.googleapis.com"})

    def __init__(self, api_key: Optional[str], timeout_seconds: float = 30.0, *, mock_mode: bool = True, **kwargs: Any) -> None:
        super().__init__(api_key, timeout_seconds, base_url=_GEMINI_BASE_URL, mock_mode=mock_mode, **kwargs)

    @property
    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(provider=self.name, configured=self.configured, capabilities={Capability.CHAT, Capability.STREAMING, Capability.EMBEDDINGS, Capability.SYSTEM_MESSAGES})

    @staticmethod
    def _resolve_model(model: str) -> str:
        return {"gemini-pro": "gemini-1.0-pro", "gemini-flash": "gemini-1.5-flash", "gemini-ultra": "gemini-1.0-ultra"}.get(model, model)

    @staticmethod
    def _map_finish_reason(reason: str | None) -> str:
        return {"STOP": "stop", "MAX_TOKENS": "length", "SAFETY": "content_filter", "RECITATION": "content_filter", "OTHER": "stop", "FINISH_REASON_UNSPECIFIED": "stop"}.get(str(reason or "").upper(), "stop")

    def _payload(self, request: ChatCompletionRequest) -> dict[str, Any]:
        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            role = "model" if message.role == "assistant" else "user"
            parts = message.content if isinstance(message.content, list) else [{"text": message.content}]
            if message.role == "system":
                system_parts.extend(parts if isinstance(parts, list) else [{"text": str(parts)}])
            else:
                contents.append({"role": role, "parts": parts})
        payload: dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": request.temperature}}
        if request.max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = request.max_tokens
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        return payload

    def _url(self, model: str, operation: str) -> str:
        return f"{self._base_url}/models/{self._resolve_model(model)}:{operation}"

    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key and self.mock_mode:
            return self._mock_chat(request)
        if not self.api_key:
            raise self._error_from_missing_secret()
        client = await self._get_client()
        response = await client.post(self._url(request.model, "generateContent"), json=self._payload(request), headers={"x-goog-api-key": self.api_key})
        self._raise_for_response(response)
        return self._parse_generate_response(self._json(response, self.name), request.model)

    async def _chat_stream_impl(self, request: ChatCompletionRequest) -> AsyncIterator[ChatCompletionChunk]:
        if not self.api_key and self.mock_mode:
            async for chunk in self._mock_stream(request):
                yield chunk
            return
        if not self.api_key:
            raise self._error_from_missing_secret()
        client = await self._get_client()
        async with client.stream("POST", self._url(request.model, "streamGenerateContent") + "?alt=sse", json=self._payload(request), headers={"x-goog-api-key": self.api_key}) as response:
            self._raise_for_response(response)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    chunk = self._parse_stream_chunk(json.loads(raw), request.model)
                except (ValueError, TypeError, KeyError) as exc:
                    raise ProviderError("Provider returned malformed stream data.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc
                if chunk is not None:
                    yield chunk

    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self.api_key and self.mock_mode:
            return self._mock_embedding(request)
        if not self.api_key:
            raise self._error_from_missing_secret()
        inputs = request.input if isinstance(request.input, list) else [request.input]
        client = await self._get_client()
        vectors: list[EmbeddingVector] = []
        for index, text in enumerate(inputs):
            response = await client.post(self._url(request.model, "embedContent"), json={"model": f"models/{self._resolve_model(request.model)}", "content": {"parts": [{"text": text}]}}, headers={"x-goog-api-key": self.api_key})
            self._raise_for_response(response)
            data = self._json(response, self.name)
            try:
                vectors.append(EmbeddingVector(index=index, embedding=[float(value) for value in data["embedding"]["values"]]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderError("Provider returned malformed embedding response.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc
        return EmbeddingResponse(data=vectors, model=request.model, provider=self.name, usage=UsageInfo(prompt_tokens=0, total_tokens=0))

    def _parse_generate_response(self, data: dict[str, Any], model: str) -> ChatCompletionResponse:
        try:
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
            text = "".join(str(part.get("text", "")) for part in parts)
            usage_meta = data.get("usageMetadata") or {}
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Provider returned malformed chat response.", provider=self.name, retriable=False, details={"classification": "malformed_response"}) from exc
        prompt = int(usage_meta.get("promptTokenCount", 0) or 0)
        completion = int(usage_meta.get("candidatesTokenCount", 0) or 0)
        total = int(usage_meta.get("totalTokenCount", prompt + completion) or 0)
        return ChatCompletionResponse(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=model, provider=self.name, choices=[ChatChoice(index=int(candidate.get("index", 0)), message=ChatMessage(role="assistant", content=text), finish_reason=self._map_finish_reason(candidate.get("finishReason")))], usage=UsageInfo(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total))

    def _parse_stream_chunk(self, data: Dict[str, Any], model: str) -> Optional[ChatCompletionChunk]:
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(str(part.get("text", "")) for part in parts)
        reason = candidate.get("finishReason")
        return ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=model, provider=self.name, choices=[ChatCompletionChunkChoice(index=int(candidate.get("index", 0)), delta=ChatCompletionChunkDelta(role="assistant" if not text else None, content=text or None), finish_reason=self._map_finish_reason(reason) if reason else None)])

    def _error_from_missing_secret(self) -> ProviderError:
        from ..contracts import ErrorClass
        return self._error(ErrorClass.AUTHENTICATION, "Provider authentication is not configured.", retryable=False)

    def _mock_chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return ChatCompletionResponse(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatChoice(index=0, message=ChatMessage(role="assistant", content=f"[Google Gemini mock] Response to: {request.messages[-1].content}"), finish_reason="stop")], usage=UsageInfo(prompt_tokens=10, completion_tokens=15, total_tokens=25))

    async def _mock_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatCompletionChunk]:
        words = f"[Google Gemini mock stream] {request.messages[-1].content}".split()
        for index, word in enumerate(words):
            yield ChatCompletionChunk(id=f"chatcmpl-{uuid.uuid4().hex}", created=int(time.time()), model=request.model, provider=self.name, choices=[ChatCompletionChunkChoice(index=0, delta=ChatCompletionChunkDelta(content=f"{word} "), finish_reason="stop" if index == len(words) - 1 else None)])

    def _mock_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        items = request.input if isinstance(request.input, list) else [request.input]
        return EmbeddingResponse(data=[EmbeddingVector(index=i, embedding=[0.1, 0.2, 0.3, 0.4]) for i, _ in enumerate(items)], model=request.model, provider=self.name, usage=UsageInfo(prompt_tokens=len(items) * 5, total_tokens=len(items) * 5))
