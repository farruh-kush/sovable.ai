from __future__ import annotations

import pytest
from ai_routing_shared.exceptions import DependencyUnavailableError, RateLimitError
from auth.security.rate_limit import AuthRateLimiter


@pytest.mark.asyncio
async def test_auth_rate_limit_rejects_replay_burst() -> None:
    limiter = AuthRateLimiter()
    await limiter.check("login:ip:email", limit=2, window_seconds=60)
    await limiter.check("login:ip:email", limit=2, window_seconds=60)
    with pytest.raises(RateLimitError):
        await limiter.check("login:ip:email", limit=2, window_seconds=60)


@pytest.mark.asyncio
async def test_redis_rate_limit_path_is_enforced() -> None:
    class FakeRedis:
        def __init__(self):
            self.count = 0
            self.expiry = None

        async def incr(self, key):
            self.count += 1
            return self.count

        async def expire(self, key, seconds):
            self.expiry = seconds

    limiter = AuthRateLimiter()
    limiter._backend = "redis"
    limiter._redis = FakeRedis()
    await limiter.check("login:redis", limit=1, window_seconds=60)
    with pytest.raises(RateLimitError):
        await limiter.check("login:redis", limit=1, window_seconds=60)
    assert limiter._redis.expiry == 60


@pytest.mark.asyncio
async def test_redis_rate_limit_backend_fails_closed_when_unavailable() -> None:
    limiter = AuthRateLimiter()
    limiter._backend = "redis"
    with pytest.raises(DependencyUnavailableError):
        await limiter.check("login:unavailable", limit=1, window_seconds=60)


@pytest.mark.asyncio
async def test_auth_rate_limit_isolated_by_identifier() -> None:
    limiter = AuthRateLimiter()
    await limiter.check("login:one", limit=1, window_seconds=60)
    await limiter.check("login:two", limit=1, window_seconds=60)
    await limiter.clear()
    await limiter.check("login:one", limit=1, window_seconds=60)
