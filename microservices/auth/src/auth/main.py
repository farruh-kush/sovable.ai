"""FastAPI application entry point for the Auth Service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic

from ai_routing_shared.middleware import RequestIdMiddleware, error_handler_middleware
from ai_routing_shared.utils import configure_logging, get_logger
from fastapi import FastAPI, Request

from .api.identity import router as identity_router
from .api.keys import router as keys_router
from .api.validate import router as validate_router
from .core.config import get_settings
from .db.database import init_db
from .security.rate_limit import limiter

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, service_name="auth")
    if (
        settings.app_env == "production"
        and settings.secret_key.get_secret_value() == "change-me-in-production"
    ):
        raise RuntimeError("SECRET_KEY must be set in production")
    limiter.configure(settings.rate_limit_backend, settings.redis_url)
    await init_db()
    try:
        yield
    finally:
        await limiter.close()


async def access_log_middleware(request: Request, call_next):
    started = monotonic()
    response = await call_next(request)
    logger.info(
        "auth_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=round((monotonic() - started) * 1000, 2),
    )
    return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Routing Layer - Auth Service",
        version="0.3.0",
        description="Identity registration, federated login, sessions, and API-key management.",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIdMiddleware)
    app.middleware("http")(access_log_middleware)
    app.include_router(identity_router, tags=["Identity"])
    app.include_router(validate_router, prefix="/internal", tags=["Internal"])
    app.include_router(validate_router, prefix="/v1/internal", tags=["Internal"])
    app.include_router(keys_router, prefix="/internal/keys", tags=["Internal"])
    app.include_router(keys_router, prefix="/v1/keys", tags=["API Keys"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "auth"}

    return app


app = create_app()
