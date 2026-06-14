"""Auth & Identity Service — application entry point.

Manages API keys, user identities, and access policies. Exposes
internal endpoints consumed by the Gateway Service, not by external clients.

Author: Farruh
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from ai_routing_shared.middleware import RequestIdMiddleware, error_handler_middleware
from ai_routing_shared.utils import configure_logging

from .api import internal_router
from .core.config import get_settings
from .db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise the database on startup."""
    settings = get_settings()
    configure_logging(level=settings.log_level, service_name="auth")
    await init_db()
    yield


def create_app() -> FastAPI:
    """Application factory for the Auth & Identity Service."""
    app = FastAPI(
        title="AI Routing Layer — Auth Service",
        version="0.1.0",
        description="Internal API key management and authentication service.",
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(internal_router, prefix="/internal", tags=["Internal"])

    return app


app = create_app()
