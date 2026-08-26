"""Shared provider-adapter runtime with safe resilience primitives."""
from __future__ import annotations

import asyncio
import json
import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import monotonic
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, TypeVar

import httpx

from ai_routing_shared.exceptions import ProviderCircuitOpenError, ProviderError
from ai_routing_shared.models import ChatCompletionRequest, ChatCompletionResponse, EmbeddingRequest, EmbeddingResponse
from ai_routing_shared.utils import get_logger

from ..contracts import CapabilitySet, ErrorClass, HealthResult, ProviderErrorBody

logger = get_logger(__name__)
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.15
    max_delay_seconds: float = 2.0
    jitter_seconds: float = 0.05


class ProviderHealth:
    """Small in-memory health state; no request content is retained."""

    def __init__(self, failure_threshold: int = 3, open_seconds: float = 30.0) -> None:
        self.error_count = 0
        self.circuit_open_until = 0.0
        self.last_latency_ms = 0.0
        self._failure_threshold = failure_threshold
        self._open_seconds = open_seconds
        self._lock = asyncio.Lock()

    def is_available(self) -> bool:
        return monotonic() >= self.circuit_open_until

    async def record_success(self, latency_ms: float) -> None:
        async with self._lock:
            self.error_count = 0
            self.last_latency_ms = round(latency_ms, 2)

    async def record_failure(self) -> None:
        async with self._lock:
            self.error_count += 1
            if self.error_count >= self._failure_threshold:
                self.circuit_open_until = monotonic() + self._open_seconds
                logger.warning("provider_circuit_open", provider_state="open")

    def snapshot(self, provider: str, configured: bool) -> HealthResult:
        circuit_open = not self.is_available()
        healthy = configured and not circuit_open and self.error_count == 0
        signal = "unconfigured" if not configured else "circuit_open" if circuit_open else "ready" if healthy else "degraded"
        return HealthResult(
            provider=provider,
            configured=configured,
            healthy=healthy,
            circuit_open=circuit_open,
            last_latency_ms=self.last_latency_ms,
            consecutive_failures=self.error_count,
            signal=signal,
        )


class BaseProviderAdapter(ABC):
    """Typed, replaceable interface shared by every provider implementation."""

    name = "base"
    default_base_url: str | None = None
    allowed_hosts: frozenset[str] = frozenset()

    def __init__(
        self,
        api_key: Optional[str],
        timeout_seconds: float = 30.0,
        *,
        base_url: str | None = None,
        mock_mode: bool = True,
        max_concurrency: int = 32,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = min(max(float(timeout_seconds), 0.1), 120.0)
        self.mock_mode = mock_mode
        self.retry_policy = retry_policy or RetryPolicy()
        self.health = ProviderHealth()
        self._semaphore = asyncio.Semaphore(max(1, min(max_concurrency, 256)))
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        self._base_url = self._validate_base_url(base_url or self.default_base_url)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(provider=self.name, configured=self.configured)

    def _validate_base_url(self, base_url: str | None) -> str | None:
        if base_url is None:
            return None
        parsed = httpx.URL(base_url)
        if parsed.scheme != "https" or not parsed.host:
            raise ValueError(f"Unsafe provider base URL for {self.name}.")
        if self.allowed_hosts and parsed.host not in self.allowed_hosts:
            raise ValueError(f"Provider base URL is not allowlisted for {self.name}.")
        return str(parsed).rstrip("/")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            async with self._client_lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self.timeout_seconds, connect=min(5.0, self.timeout_seconds)),
                        limits=httpx.Limits(max_connections=64, max_keepalive_connections=32, keepalive_expiry=30.0),
                        follow_redirects=False,
                    )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return await self._with_retries(self._chat_impl, request)

    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[Any]:
        if not self.health.is_available():
            raise self._error(ErrorClass.CIRCUIT_OPEN, "Provider circuit is open.", retryable=True)
        async for chunk in self._chat_stream_impl(request):
            yield chunk

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return await self._with_retries(self._embedding_impl, request)

    async def health_check(self) -> HealthResult:
        return self.health.snapshot(self.name, self.configured or self.mock_mode)

    async def _with_retries(self, func: Callable[..., Awaitable[T]], *args: Any) -> T:
        if not self.health.is_available():
            raise ProviderCircuitOpenError("Provider circuit is open.", provider=self.name, retriable=True, details={"classification": ErrorClass.CIRCUIT_OPEN.value})
        last_error: ProviderError | None = None
        attempts = self.retry_policy.max_attempts
        async with self._semaphore:
            for attempt in range(attempts):
                started = monotonic()
                try:
                    result = await func(*args)
                    await self.health.record_success((monotonic() - started) * 1000)
                    return result
                except asyncio.CancelledError:
                    logger.info("provider_request_cancelled", provider=self.name)
                    raise
                except ProviderError as exc:
                    last_error = exc
                    if not exc.retriable or attempt >= attempts - 1:
                        await self.health.record_failure()
                        raise
                    await self.health.record_failure()
                    retry_after = float(exc.details.get("retry_after_seconds", 0.0) or 0.0)
                    await asyncio.sleep(max(self._backoff(attempt), min(retry_after, 120.0)))
                except (httpx.TimeoutException, TimeoutError) as exc:
                    last_error = self._error(ErrorClass.TIMEOUT, "Provider request timed out.", retryable=True, cause=exc)
                    await self.health.record_failure()
                    if attempt >= attempts - 1:
                        raise last_error
                    await asyncio.sleep(self._backoff(attempt))
                except httpx.RequestError as exc:
                    last_error = self._error(ErrorClass.NETWORK, "Provider network request failed.", retryable=True, cause=exc)
                    await self.health.record_failure()
                    if attempt >= attempts - 1:
                        raise last_error
                    await asyncio.sleep(self._backoff(attempt))
                except Exception as exc:
                    await self.health.record_failure()
                    raise self._error(ErrorClass.MALFORMED_RESPONSE, "Provider response could not be normalized.", retryable=False, cause=exc) from exc
        raise last_error or self._error(ErrorClass.NETWORK, "Provider request failed.", retryable=True)

    def _backoff(self, attempt: int) -> float:
        delay = min(self.retry_policy.max_delay_seconds, self.retry_policy.base_delay_seconds * (2**attempt))
        return delay + random.uniform(0, self.retry_policy.jitter_seconds)

    def _error(
        self,
        classification: ErrorClass,
        message: str,
        *,
        retryable: bool,
        status_code: int | None = None,
        retry_after: float | None = None,
        provider_request_id: str | None = None,
        cause: BaseException | None = None,
    ) -> ProviderError:
        details = ProviderErrorBody(
            provider=self.name,
            classification=classification,
            retryable=retryable,
            correlation_id=str(uuid.uuid4()),
            provider_request_id=provider_request_id,
            retry_after_seconds=retry_after,
            message=message,
        ).model_dump(exclude_none=True)
        if status_code is not None:
            details["status_code"] = status_code
        return ProviderError(message, provider=self.name, retriable=retryable, details=details)

    def _raise_for_response(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        status = response.status_code
        retry_after: float | None = None
        raw_retry_after = response.headers.get("retry-after")
        if raw_retry_after:
            try:
                retry_after = max(0.0, min(float(raw_retry_after), 120.0))
            except ValueError:
                retry_after = None
        if status in {401, 403}:
            classification, retryable = ErrorClass.AUTHENTICATION, False
        elif status == 429:
            classification, retryable = ErrorClass.RATE_LIMIT, True
        elif status in {408, 409, 425} or status >= 500:
            classification, retryable = ErrorClass.SERVER_ERROR, True
        elif status in {400, 404, 413, 422}:
            classification, retryable = ErrorClass.INVALID_REQUEST, False
        else:
            classification, retryable = ErrorClass.SERVER_ERROR, True
        provider_request_id = response.headers.get("x-request-id") or response.headers.get("request-id")
        raise self._error(classification, f"{self.name} provider returned HTTP {status}.", retryable=retryable, status_code=status, retry_after=retry_after, provider_request_id=provider_request_id)

    @staticmethod
    def _json(response: httpx.Response, provider: str) -> dict[str, Any]:
        try:
            value = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ProviderError("Provider returned malformed JSON.", provider=provider, retriable=False, details={"classification": ErrorClass.MALFORMED_RESPONSE.value}) from exc
        if not isinstance(value, dict):
            raise ProviderError("Provider returned an unexpected JSON shape.", provider=provider, retriable=False, details={"classification": ErrorClass.MALFORMED_RESPONSE.value})
        return value

    @abstractmethod
    async def _chat_impl(self, request: ChatCompletionRequest) -> ChatCompletionResponse: ...

    @abstractmethod
    async def _chat_stream_impl(self, request: ChatCompletionRequest) -> AsyncIterator[Any]: ...

    @abstractmethod
    async def _embedding_impl(self, request: EmbeddingRequest) -> EmbeddingResponse: ...

    async def discover_capabilities(self) -> CapabilitySet:
        return self.capabilities
