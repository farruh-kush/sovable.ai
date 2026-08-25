"""Provider Adapter Service — application entry point.

The abstraction layer for all external LLM providers. Normalises
provider-specific request/response formats into the unified schema.

Author: Farruh
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from ai_routing_shared.middleware import RequestIdMiddleware, error_handler_middleware
from ai_routing_shared.utils import configure_logging
from fastapi import FastAPI

from .api import router as adapt_router
from .core.config import get_settings
from .core.registry import ProviderRegistry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise the provider registry on startup."""
    settings = get_settings()
    configure_logging(level=settings.log_level, service_name="provider")
    app.state.registry = ProviderRegistry(settings=settings)
    yield


def create_app() -> FastAPI:
    """Application factory for the Provider Adapter Service."""
    app = FastAPI(
        title="AI Routing Layer — Provider Adapter",
        version="0.1.0",
        description="Normalises requests and responses across LLM providers.",
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(adapt_router, prefix="/adapt", tags=["Adapters"])

    return app


app = create_app()
