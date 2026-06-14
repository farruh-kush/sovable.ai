from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import monotonic
from typing import Any, Optional

import httpx

from ai_routing_layer.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderErrorPayload,
)


class ProviderError(Exception):
    def __init__(self, payload: ProviderErrorPayload) -> None:
        super().__init__(payload.message)
        self.payload = payload


@dataclass
class ProviderHealth:
    error_count: int = 0
    circuit_open_until: float = 0.0
    last_latency_ms: float = 50.0

    def available(self) -> bool:
        return monotonic() >= self.circuit_open_until


class BaseProvider(ABC):
    name: str

    def __init__(self, api_key: Optional[str], timeout_seconds: float = 30.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.health = ProviderHealth()

    @abstractmethod
    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatCompletionChunk]:
        raise NotImplementedError

    @abstractmethod
    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        raise NotImplementedError

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text.split()))

    async def _request_with_retries(
        self,
        func: Any,
        *args: Any,
        retries: int = 2,
        **kwargs: Any,
    ) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            if not self.health.available():
                raise ProviderError(
                    ProviderErrorPayload(
                        code="circuit_open",
                        message=f"{self.name} provider circuit is open",
                        provider=self.name,
                        retriable=True,
                    )
                )
            try:
                start = monotonic()
                result = await func(*args, **kwargs)
                self.health.error_count = 0
                self.health.last_latency_ms = (monotonic() - start) * 1000
                return result
            except (httpx.HTTPError, asyncio.TimeoutError, ProviderError) as exc:
                last_error = exc
                self.health.error_count += 1
                if self.health.error_count >= 3:
                    self.health.circuit_open_until = monotonic() + 30
                if attempt == retries:
                    break
                await asyncio.sleep(0.1 * (attempt + 1))
        if isinstance(last_error, ProviderError):
            raise last_error
        raise ProviderError(
            ProviderErrorPayload(
                code="provider_error",
                message=str(last_error),
                provider=self.name,
                retriable=True,
            )
        )


class ProviderRegistry:
    def __init__(self, providers: list[BaseProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def get(self, name: str) -> BaseProvider:
        return self._providers[name]

    def all(self) -> list[BaseProvider]:
        return list(self._providers.values())

    def health_snapshot(self) -> dict[str, ProviderHealth]:
        return {name: provider.health for name, provider in self._providers.items()}


__all__ = [
    "ProviderError",
    "ProviderHealth",
    "BaseProvider",
    "ProviderRegistry",
    "ProviderErrorPayload",
]
