"""Provider Adapter Service entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from ai_routing_shared.middleware.error_handler import error_handler_middleware
from ai_routing_shared.middleware.request_id import RequestIdMiddleware
from ai_routing_shared.utils import configure_logging

from .api import router
from .core.config import get_settings
from .core.registry import ProviderRegistry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level, service_name="provider")
    registry = ProviderRegistry(settings)
    app.state.registry = registry
    try:
        yield
    finally:
        await registry.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="AI Routing Layer Provider Adapter", version="1.0.0", lifespan=lifespan)
    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(router, prefix="/v1/adapt")
    # Backward-compatible public route family used by existing Gateway clients.
    app.include_router(router, prefix="/adapt")
    return app


app = create_app()
