"""Redis client for the API Gateway Service.

Implements the **true sliding window** rate limiter described in
Phase 1 — Task 1.1 of the implementation plan, using Redis Sorted Sets
with timestamps as scores. This replaces the broken INCR+EXPIRE approach
that caused permanent lockouts.

Author: Farruh
"""

from __future__ import annotations

import time

import redis.asyncio as aioredis

from ai_routing_shared.exceptions import RateLimitError
from ai_routing_shared.utils import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Async Redis client with sliding window rate limiting."""

    def __init__(self, url: str) -> None:
        self._url = url
        self.client: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Open the connection pool."""
        self.client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        await self.client.ping()
        logger.info("redis_connected", url=self._url)

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self.client:
            await self.client.aclose()

    # ── Phase 1 — Task 1.1: True Sliding Window Rate Limiter ────────────────

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """Check whether a request is within the sliding window rate limit.

        Uses a Redis Sorted Set where each member is a unique timestamp string
        and the score is the Unix timestamp. Expired entries are pruned on
        every call, so the window truly slides rather than resetting.

        Args:
            key: Unique identifier for the rate limit bucket (e.g. ``"rl:key_abc:minute"``).
            limit: Maximum number of requests allowed within ``window_seconds``.
            window_seconds: Duration of the sliding window in seconds.

        Returns:
            ``True`` if the request is within the limit, ``False`` otherwise.

        Raises:
            RateLimitError: If the limit has been exceeded.
        """
        assert self.client is not None, "Redis client not connected"

        now = time.time()
        window_start = now - window_seconds

        async with self.client.pipeline(transaction=True) as pipe:
            # Remove entries that have fallen outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            # Record the current request (score = timestamp, member = unique str)
            pipe.zadd(key, {f"{now:.6f}": now})
            # Count requests remaining in the window
            pipe.zcard(key)
            # Set TTL so the key is cleaned up automatically
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

        count: int = results[2]
        allowed = count <= limit

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                key=key,
                count=count,
                limit=limit,
                window_seconds=window_seconds,
            )

        return allowed

    # ── Prompt Caching (Phase 3 — Task 3.2) ─────────────────────────────────

    async def get_cached_response(self, cache_key: str) -> str | None:
        """Return a cached completion response, or ``None`` on a miss."""
        assert self.client is not None
        return await self.client.get(f"cache:{cache_key}")

    async def set_cached_response(
        self, cache_key: str, response: str, ttl_seconds: int = 3600
    ) -> None:
        """Store a completion response in the cache."""
        assert self.client is not None
        await self.client.setex(f"cache:{cache_key}", ttl_seconds, response)

    # ── Monthly Spend (Phase 1 — Task 1.2) ──────────────────────────────────

    async def get_monthly_spend(self, api_key_id: str) -> float:
        """Return the current month's spend for an API key in USD.

        The Billing Service is the source of truth; this is a fast Redis
        read-through cache updated after every billing event.
        """
        assert self.client is not None
        value = await self.client.get(f"spend:{api_key_id}:monthly")
        return float(value) if value else 0.0
