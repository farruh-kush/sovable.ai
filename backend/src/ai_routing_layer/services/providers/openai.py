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


class OpenAIProvider(BaseProvider):
    name = "openai"
    base_url = "https://api.openai.com/v1"

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return await self._request_with_retries(self._chat, request)

    async def _chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key:
            return self._mock_chat_response(request)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = request.model_dump(exclude_none=True)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            if response.status_code >= 400:
                raise ProviderError(
                    ProviderErrorPayload(
                        code="openai_error",
                        message=response.text,
                        provider=self.name,
                        retriable=response.status_code >= 500,
                    )
                )
            data = response.json()
        usage = UsageInfo(**data.get("usage", {}))
        return ChatCompletionResponse(
            id=data["id"],
            created=data["created"],
            model=data["model"],
            provider=self.name,
            choices=[
                ChatChoice(
                    index=choice["index"],
                    message=ChatMessage(**choice["message"]),
                    finish_reason=choice.get("finish_reason"),
                )
                for choice in data["choices"]
            ],
            usage=usage,
        )

    async def chat_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[ChatCompletionChunk]:
        if not self.api_key:
            text = self._mock_text(request)
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
                        index=0,
                        delta=ChatCompletionChunkDelta(),
                        finish_reason="stop",
                    )
                ],
            )
            return
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as response:
                if response.status_code >= 400:
                    raise ProviderError(
                        ProviderErrorPayload(
                            code="openai_error",
                            message=(await response.aread()).decode("utf-8", errors="replace"),
                            provider=self.name,
                            retriable=response.status_code >= 500,
                        )
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    data = httpx.Response(200, text=line[6:]).json()
                    yield ChatCompletionChunk(
                        id=data["id"],
                        created=data["created"],
                        model=data["model"],
                        provider=self.name,
                        choices=[
                            ChatCompletionChunkChoice(
                                index=choice["index"],
                                delta=ChatCompletionChunkDelta(**choice.get("delta", {})),
                                finish_reason=choice.get("finish_reason"),
                            )
                            for choice in data["choices"]
                        ],
                    )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self.api_key:
            return self._mock_embedding_response(request)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = request.model_dump(exclude_none=True)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/embeddings", json=payload, headers=headers
            )
            if response.status_code >= 400:
                raise ProviderError(
                    ProviderErrorPayload(
                        code="openai_error",
                        message=response.text,
                        provider=self.name,
                        retriable=response.status_code >= 500,
                    )
                )
            data = response.json()
        usage = UsageInfo(**data.get("usage", {}))
        return EmbeddingResponse(
            data=[EmbeddingVector(**item) for item in data["data"]],
            model=data["model"],
            provider=self.name,
            usage=usage,
        )

    def _mock_text(self, request: ChatCompletionRequest) -> str:
        prompt = " ".join(message.content for message in request.messages)
        return f"Mock OpenAI response to: {prompt}"

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
            id=f"chatcmpl-{uuid.uuid4().hex}",
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
                EmbeddingVector(index=index, embedding=[float(index), 0.1, 0.2, 0.3])
                for index, _ in enumerate(items)
            ],
            model=request.model,
            provider=self.name,
            usage=usage,
        )
