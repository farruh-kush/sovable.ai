"""Auth and Identity Service application entry point.
Author: Farruh
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from ai_routing_shared.middleware import RequestIdMiddleware, error_handler_middleware
from ai_routing_shared.utils import configure_logging
from fastapi import FastAPI

from .api.identity import router as identity_router
from .api.keys import router as keys_router
from .api.validate import router as validate_router
from .core.config import get_settings
from .db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, service_name="auth")
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Routing Layer - Auth Service",
        version="0.2.0",
        description="Identity registration, federated login, sessions, and API-key management.",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(identity_router, tags=["Identity"])
    app.include_router(validate_router, prefix="/internal", tags=["Internal"])
    app.include_router(keys_router, prefix="/internal/keys", tags=["Internal"])

    @app.get("/health")
    async def health() -> dict:
        return {"status": "healthy", "service": "auth"}

    return app


app = create_app()
