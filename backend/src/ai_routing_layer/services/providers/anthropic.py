from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

import httpx

from ai_routing_layer.models import (
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
    ProviderErrorPayload,
    UsageInfo,
)
from ai_routing_layer.providers.base import BaseProvider, ProviderError


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    base_url = "https://api.anthropic.com/v1"

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return await self._request_with_retries(self._chat, request)

    async def _chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key:
            return self._mock_chat_response(request)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        system_messages = [
            message.content for message in request.messages if message.role == "system"
        ]
        user_messages = [
            {"role": "user" if message.role == "user" else "assistant", "content": message.content}
            for message in request.messages
            if message.role != "system"
        ]
        payload = {
            "model": request.model,
            "system": "\n".join(system_messages) if system_messages else None,
            "messages": user_messages,
            "max_tokens": request.max_tokens or 512,
            "temperature": request.temperature,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/messages", json=payload, headers=headers)
            if response.status_code >= 400:
                raise ProviderError(
                    ProviderErrorPayload(
                        code="anthropic_error",
                        message=response.text,
                        provider=self.name,
                        retriable=response.status_code >= 500,
                    )
                )
            data = response.json()
        text = "".join(block["text"] for block in data["content"] if block["type"] == "text")
        usage = UsageInfo(
            prompt_tokens=data.get("usage", {}).get("input_tokens", 0),
            completion_tokens=data.get("usage", {}).get("output_tokens", 0),
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ChatCompletionResponse(
            id=data["id"],
            created=int(time.time()),
            model=request.model,
            provider=self.name,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=text),
                    finish_reason="stop",
                )
            ],
            usage=usage,
        )

    async def chat_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        text = (
            self._mock_text(request)
            if not self.api_key
            else "Anthropic streaming passthrough not implemented in starter"
        )
        for token in text.split():
            yield ChatCompletionChunk(
                id=f"chatcmpl-{uuid.uuid4().hex}",
                created=int(time.time()),
                model=request.model,
                provider=self.name,
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChatCompletionChunkDelta(content=f"{token} "),
                        finish_reason=None,
                    )
                ],
            )
        yield ChatCompletionChunk(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            provider=self.name,
            choices=[
                ChatCompletionChunkChoice(
                    index=0, delta=ChatCompletionChunkDelta(), finish_reason="stop"
                )
            ],
        )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return self._mock_embedding_response(request)

    def _mock_text(self, request: ChatCompletionRequest) -> str:
        prompt = " ".join(message.content for message in request.messages)
        return f"Mock Anthropic response to: {prompt}"

    def _mock_chat_response(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        text = self._mock_text(request)
        usage = UsageInfo(
            prompt_tokens=sum(
                self.estimate_tokens(message.content) for message in request.messages
            ),
            completion_tokens=self.estimate_tokens(text),
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ChatCompletionResponse(
            id=f"msg-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            provider=self.name,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=text),
                    finish_reason="stop",
                )
            ],
            usage=usage,
        )

    def _mock_embedding_response(self, request: EmbeddingRequest) -> EmbeddingResponse:
        items = request.input if isinstance(request.input, list) else [request.input]
        usage = UsageInfo(
            prompt_tokens=sum(self.estimate_tokens(item) for item in items), total_tokens=0
        )
        usage.total_tokens = usage.prompt_tokens
        return EmbeddingResponse(
            data=[
                EmbeddingVector(index=index, embedding=[0.5, float(index), 0.25, 0.75])
                for index, _ in enumerate(items)
            ],
            model=request.model,
            provider=self.name,
            usage=usage,
        )
