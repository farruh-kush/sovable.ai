"""API Gateway Service — application entry point.

This service is the single HTTPS entry point for all client requests.
It is responsible for:
  1. Request validation and authentication (via Auth Service)
  2. Rate limiting (Phase 1 — Task 1.1: Redis sliding window)
  3. Monthly budget enforcement (Phase 1 — Task 1.2)
  4. Model whitelist enforcement (Phase 1 — Task 1.3)
  5. Forwarding validated requests to the Router Engine Service

Author: Farruh
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_routing_shared.middleware import RequestIdMiddleware, error_handler_middleware
from ai_routing_shared.utils import configure_logging

from .api.v1 import chat, embeddings, keys, models, generations, health
from .core.config import get_settings
from .core.redis_client import RedisClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of shared resources."""
    settings = get_settings()
    configure_logging(level=settings.log_level, service_name="gateway")

    # Initialise Redis connection pool
    redis = RedisClient(url=settings.redis_url)
    await redis.connect()
    app.state.redis = redis

    yield

    await redis.disconnect()


def create_app() -> FastAPI:
    """Application factory for the API Gateway Service."""
    settings = get_settings()

    app = FastAPI(
        title="AI Routing Layer — API Gateway",
        version="0.1.0",
        description="Unified OpenAI-compatible API gateway for multiple LLM providers.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Middleware stack (applied in reverse order — last added = outermost)
    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Route registration
    app.include_router(health.router, tags=["Health"])
    app.include_router(chat.router, prefix="/v1", tags=["Chat Completions"])
    app.include_router(embeddings.router, prefix="/v1", tags=["Embeddings"])
    app.include_router(keys.router, prefix="/v1", tags=["API Keys"])
    app.include_router(models.router, prefix="/v1", tags=["Models"])
    app.include_router(generations.router, prefix="/v1", tags=["Generations"])

    return app


app = create_app()
