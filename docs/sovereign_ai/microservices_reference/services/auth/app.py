from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException

from shared.config import settings
from shared.models import AuthorizeRequest, AuthorizeResponse, HealthResponse, Principal


config = settings("auth", 8101)
app = FastAPI(title="AI Routing Auth Service", version="0.1.0")

# Local reference credentials. Production uses a hashed API-key store in auth_db.
KEYS = {
    config.gateway_api_key: Principal(
        api_key_id="key-local-demo",
        subject="demo-user",
        organization_id="demo-org",
        tier="paid",
        scopes=["chat:complete", "embeddings:create"],
    ),
    "sk-local-admin": Principal(
        api_key_id="key-local-admin",
        subject="admin-user",
        organization_id="platform-org",
        tier="admin",
        scopes=["chat:complete", "embeddings:create", "admin:*"],
    ),
}


def require_internal(secret: str | None) -> None:
    if secret != config.internal_secret:
        raise HTTPException(status_code=401, detail="invalid internal service credential")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=config.service_name, status="ok")


@app.post("/internal/authorize", response_model=AuthorizeResponse)
async def authorize(payload: AuthorizeRequest, x_internal_secret: str | None = Header(default=None)) -> AuthorizeResponse:
    require_internal(x_internal_secret)
    principal = KEYS.get(payload.api_key)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid API key")
    if payload.required_scope not in principal.scopes and "admin:*" not in principal.scopes:
        raise HTTPException(status_code=403, detail="missing required scope")
    return AuthorizeResponse(principal=principal)
