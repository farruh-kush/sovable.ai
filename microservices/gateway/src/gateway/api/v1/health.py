"""Health check endpoint.

Author: Farruh
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    """Return the health status of the gateway and its dependencies."""
    redis_ok = False
    try:
        await request.app.state.redis.client.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "gateway",
        "dependencies": {
            "redis": "ok" if redis_ok else "unavailable",
        },
    }
