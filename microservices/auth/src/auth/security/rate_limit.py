"""Async rate limiting for auth issuance endpoints.

Production deployments configure Redis so limits are shared across replicas.
The in-memory mode is useful for local development and unit tests only.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from time import monotonic

from ai_routing_shared.exceptions import DependencyUnavailableError, RateLimitError


class AuthRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._redis = None
        self._backend = "memory"

    def configure(self, backend: str, redis_url: str) -> None:
        self._backend = backend.lower()
        if self._backend == "redis":
            from redis.asyncio import Redis

            self._redis = Redis.from_url(redis_url, decode_responses=True)

    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        if self._backend == "redis":
            await self._check_redis(key, limit, window_seconds)
            return
        await self._check_memory(key, limit, window_seconds)

    async def _check_memory(self, key: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        cutoff = now - window_seconds
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                raise RateLimitError(
                    "Too many authentication requests. Try again later.",
                    details={"retry_after_seconds": max(1, window_seconds)},
                )
            events.append(now)

    async def _check_redis(self, key: str, limit: int, window_seconds: int) -> None:
        if self._redis is None:
            raise DependencyUnavailableError("Authentication rate-limit backend is unavailable.")
        redis_key = f"auth:rate:{key}"
        try:
            count = await self._redis.incr(redis_key)
            if count == 1:
                await self._redis.expire(redis_key, window_seconds)
            if count > limit:
                raise RateLimitError(
                    "Too many authentication requests. Try again later.",
                    details={"retry_after_seconds": max(1, window_seconds)},
                )
        except RateLimitError:
            raise
        except Exception as exc:
            raise DependencyUnavailableError(
                "Authentication rate-limit backend is unavailable."
            ) from exc

    async def clear(self) -> None:
        async with self._lock:
            self._events.clear()

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


limiter = AuthRateLimiter()
