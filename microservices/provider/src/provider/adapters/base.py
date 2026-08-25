"""Base provider adapter with circuit breaker and retry logic.

Every provider adapter inherits from ``BaseProviderAdapter`` and implements
the ``_chat_impl`` and ``_embedding_impl`` abstract methods. The base class
handles retries, circuit breaking, and latency tracking.

Author: Farruh
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from time import monotonic
from typing import Any

from ai_routing_shared.exceptions import ProviderCircuitOpenError, ProviderError
from ai_routing_shared.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from ai_routing_shared.utils import get_logger

logger = get_logger(__name__)

_CIRCUIT_OPEN_SECONDS = 30
_ERROR_THRESHOLD = 3
_MAX_RETRIES = 2


class ProviderHealth:
    """Tracks circuit breaker state and rolling latency for a provider."""

    def __init__(self) -> None:
        self.error_count: int = 0
        self.circuit_open_until: float = 0.0
        self.last_latency_ms: float = 0.0

    def is_available(self) -> bool:
        """Return ``True`` if the circuit breaker is CLOSED."""
        return monotonic() >= self.circuit_open_until

    def record_success(self, latency_ms: float) -> None:
        self.error_count = 0
        self.last_latency_ms = latency_ms

    def record_failure(self) -> None:
        self.error_count += 1
        if self.error_count >= _ERROR_THRESHOLD:
            self.circuit_open_until = monotonic() + _CIRCUIT_OPEN_SECONDS
            logger.warning(
                "circuit_breaker_opened",
                open_until=self.circuit_open_until,
            )


class BaseProviderAdapter(ABC):
    """Abstract base class for all LLM provider adapters."""

    name: str = "base"

    def __init__(self, api_key: str | None, timeout_seconds: float = 30.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.health = ProviderHealth()

    # ── Public Interface ─────────────────────────────────────────────────────

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Execute a chat completion with retry and circuit breaker logic."""
        return await self._with_retries(self._chat_impl, request)

    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[Any]:
        """Execute a streaming chat completion."""
        async for chunk in self._chat_stream_impl(request):
            yield chunk

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Execute an embedding request with retry and circuit breaker logic."""
        return await self._with_retries(self._embedding_impl, request)

    # ── Abstract Methods ─────────────────────────────────────────────────────

    @abstractmethod
    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Provider-specific chat completion implementation."""
        ...

    @abstractmethod
    async def _chat_stream_impl(self, request: ChatCompletionRequest) -> AsyncIterator[Any]:
        """Provider-specific streaming chat implementation."""
        ...

    @abstractmethod
    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Provider-specific embedding implementation."""
        ...

    # ── Retry & Circuit Breaker ──────────────────────────────────────────────

    async def _with_retries(self, func: Any, *args: Any) -> Any:
        """Execute a provider call with retries and circuit breaker enforcement."""
        if not self.health.is_available():
            raise ProviderCircuitOpenError(
                f"Provider '{self.name}' circuit breaker is OPEN.",
                provider=self.name,
                retriable=True,
            )

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                start = monotonic()
                result = await func(*args)
                self.health.record_success((monotonic() - start) * 1000)
                return result
            except ProviderError as exc:
                last_error = exc
                self.health.record_failure()
                if not exc.retriable or attempt == _MAX_RETRIES:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))
            # Provider SDKs can expose arbitrary exception classes. Normalize them
            # here so retries and circuit-breaker accounting remain consistent.
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self.health.record_failure()
                if attempt == _MAX_RETRIES:
                    break
                await asyncio.sleep(0.1 * (attempt + 1))

        raise ProviderError(
            str(last_error),
            provider=self.name,
            retriable=True,
        )
