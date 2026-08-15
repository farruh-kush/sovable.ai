"""Router Engine Service — application entry point.

The core intelligent routing engine. Receives validated requests from the
Gateway, selects the optimal provider using configurable strategies, and
orchestrates calls to the Provider Adapter Service.

Author: Farruh
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from ai_routing_shared.middleware import RequestIdMiddleware, error_handler_middleware
from ai_routing_shared.utils import configure_logging

from .api import router as route_router
from .core.config import get_settings
from .core.redis_client import RouterRedisClient
from .engine.routing_engine import RoutingEngine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise routing engine and Redis on startup."""
    settings = get_settings()
    configure_logging(level=settings.log_level, service_name="router")

    redis = RouterRedisClient(url=settings.redis_url)
    await redis.connect()
    app.state.redis = redis

    config_path = Path(settings.routing_config_path)
    app.state.routing_engine = RoutingEngine(
        config_path=config_path,
        provider_service_url=settings.provider_service_url,
        billing_service_url=settings.billing_service_url,
        redis=redis,
    )

    yield

    await redis.disconnect()


def create_app() -> FastAPI:
    """Application factory for the Router Engine Service."""
    app = FastAPI(
        title="AI Routing Layer — Router Engine",
        version="0.1.0",
        description="Intelligent LLM routing engine with dynamic strategy selection.",
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(route_router, prefix="/route", tags=["Routing"])

    @app.get("/health")
    async def health() -> dict:
        return {"status": "healthy", "service": "router"}

    return app


app = create_app()
