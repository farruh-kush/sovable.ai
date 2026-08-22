"""Router Service Redis client.

Handles latency tracking for Phase 4 — Task 4.1 (real latency-optimised routing).
After every successful provider response, the observed latency is written to a
Redis Sorted Set keyed by ``latency:{provider}:{model}`` with a TTL of 5 minutes.

Author: Farruh
"""

from __future__ import annotations

import time
from typing import Optional

import redis.asyncio as aioredis

from ai_routing_shared.utils import get_logger

logger = get_logger(__name__)

_LATENCY_KEY_PREFIX = "latency"
_LATENCY_WINDOW_SECONDS = 300  # 5 minutes


class RouterRedisClient:
    """Async Redis client for the Router Engine Service."""

    def __init__(self, url: str) -> None:
        self._url = url
        self.client: aioredis.Redis | None = None

    async def connect(self) -> None:
        self.client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await self.client.ping()
        logger.info("redis_connected", url=self._url)

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()

    # ── Phase 4 — Task 4.1: Latency Tracking ────────────────────────────────

    async def record_latency(
        self, provider: str, model: str, latency_ms: float
    ) -> None:
        """Record an observed latency sample for a provider/model pair.

        Samples older than ``_LATENCY_WINDOW_SECONDS`` are automatically
        evicted so the rolling average reflects only recent performance.
        """
        assert self.client is not None
        key = f"{_LATENCY_KEY_PREFIX}:{provider}:{model}"
        now = time.time()
        window_start = now - _LATENCY_WINDOW_SECONDS

        async with self.client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {f"{now:.6f}:{latency_ms:.2f}": latency_ms})
            pipe.expire(key, _LATENCY_WINDOW_SECONDS)
            await pipe.execute()

    async def get_p50_latency(self, provider: str, model: str) -> Optional[float]:
        """Return the rolling P50 latency for a provider/model pair, or ``None``."""
        assert self.client is not None
        key = f"{_LATENCY_KEY_PREFIX}:{provider}:{model}"
        now = time.time()
        window_start = now - _LATENCY_WINDOW_SECONDS

        # Prune expired entries first
        await self.client.zremrangebyscore(key, 0, window_start)

        # Retrieve all scores (latency values) in the window
        members = await self.client.zrange(key, 0, -1, withscores=True)
        if not members:
            return None

        latencies = sorted(score for _, score in members)
        mid = len(latencies) // 2
        return latencies[mid]
