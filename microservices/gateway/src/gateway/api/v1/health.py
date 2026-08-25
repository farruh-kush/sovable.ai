"""Health check endpoint.

Author: Farruh
"""

from ai_routing_shared.utils import get_logger
from fastapi import APIRouter, Request
from redis.exceptions import RedisError

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health(request: Request) -> dict:
    """Return the health status of the gateway and its dependencies."""
    redis_ok = False
    try:
        await request.app.state.redis.client.ping()
        redis_ok = True
    except (RedisError, AttributeError, ConnectionError, TimeoutError) as exc:
        # Health checks must degrade gracefully, but the reason belongs in logs.
        logger.warning(
            "redis_health_check_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )

    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "gateway",
        "dependencies": {
            "redis": "ok" if redis_ok else "unavailable",
        },
    }
