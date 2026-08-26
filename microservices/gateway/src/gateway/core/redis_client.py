"""Async Redis primitives for gateway limits, cache, and spend lookups."""

from __future__ import annotations

import time
import uuid

import redis.asyncio as aioredis
from ai_routing_shared.utils import get_logger

logger = get_logger(__name__)

_RATE_LIMIT_SCRIPT = """
local now = tonumber(ARGV[1])
local window_start = now - tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local key = KEYS[1]
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
local count = redis.call('ZCARD', key)
if count >= limit then
  redis.call('EXPIRE', key, tonumber(ARGV[2]))
  return 0
end
redis.call('ZADD', key, now, ARGV[4])
redis.call('EXPIRE', key, tonumber(ARGV[2]))
return 1
"""


class RedisClient:
    """Async Redis client with atomic sliding-window rate limiting."""

    def __init__(self, url: str) -> None:
        self._url = url
        self.client: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Open the connection pool and verify connectivity."""
        self.client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        await self.client.ping()
        logger.info("redis_connected")

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Atomically consume one request when a sliding-window slot is available."""
        if limit <= 0:
            return False
        assert self.client is not None, "Redis client not connected"

        now = time.time()
        member = f"{now:.6f}:{uuid.uuid4().hex}"
        result = await self.client.eval(
            _RATE_LIMIT_SCRIPT,
            1,
            key,
            now,
            window_seconds,
            limit,
            member,
        )
        allowed = bool(result)
        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                bucket=key.rsplit(":", 1)[-1],
                limit=limit,
                window_seconds=window_seconds,
            )
        return allowed

    async def get_cached_response(self, cache_key: str) -> str | None:
        """Return a cached completion response, or ``None`` on a miss."""
        assert self.client is not None, "Redis client not connected"
        return await self.client.get(f"cache:{cache_key}")

    async def set_cached_response(
        self, cache_key: str, response: str, ttl_seconds: int = 3600
    ) -> None:
        """Store a completion response in the cache."""
        assert self.client is not None, "Redis client not connected"
        await self.client.setex(f"cache:{cache_key}", ttl_seconds, response)

    async def get_monthly_spend(self, api_key_id: str) -> float:
        """Return the current month's spend from the Billing-maintained cache."""
        assert self.client is not None, "Redis client not connected"
        value = await self.client.get(f"spend:{api_key_id}:monthly")
        return float(value) if value else 0.0
