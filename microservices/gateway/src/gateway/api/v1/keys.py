"""Admin-only API-key management proxy routes."""

from __future__ import annotations

import hmac

import httpx
from ai_routing_shared.exceptions import AuthorisationError
from ai_routing_shared.models import ApiKeyTier
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...core.config import GatewaySettings, get_settings
from ...core.downstream import request_peer, response_error_or_none, response_json

router = APIRouter()


class CreateKeyRequest(BaseModel):
    name: str
    tier: ApiKeyTier = ApiKeyTier.FREE
    monthly_budget_usd: float | None = None
    allowed_models: list[str] | None = None


def _require_admin_key(provided: str | None, expected: str) -> None:
    if not provided or not hmac.compare_digest(provided, expected):
        raise AuthorisationError("Invalid admin key.")


@router.post("/keys", response_model=None)
async def create_key(
    body: CreateKeyRequest,
    x_admin_key: str | None = Header(default=None),
    settings: GatewaySettings = Depends(get_settings),
) -> dict | JSONResponse:
    """Create a new API key through Auth (admin-only)."""
    _require_admin_key(x_admin_key, settings.admin_api_key)
    async with httpx.AsyncClient(
        base_url=settings.auth_service_url,
        timeout=httpx.Timeout(10.0, connect=3.0),
    ) as client:
        response = await request_peer(
            client,
            "POST",
            "/internal/keys",
            service="auth",
            json=body.model_dump(),
        )
    mapped = response_error_or_none(response, "auth")
    if mapped is not None:
        return mapped
    payload = response_json(response, "auth")
    return payload if isinstance(payload, dict) else {"data": payload}


@router.get("/keys", response_model=None)
async def list_keys(
    x_admin_key: str | None = Header(default=None),
    settings: GatewaySettings = Depends(get_settings),
) -> dict | JSONResponse:
    """List API-key metadata through Auth (admin-only)."""
    _require_admin_key(x_admin_key, settings.admin_api_key)
    async with httpx.AsyncClient(
        base_url=settings.auth_service_url,
        timeout=httpx.Timeout(10.0, connect=3.0),
    ) as client:
        response = await request_peer(client, "GET", "/internal/keys", service="auth")
    mapped = response_error_or_none(response, "auth")
    if mapped is not None:
        return mapped
    payload = response_json(response, "auth")
    return payload if isinstance(payload, dict) else {"data": payload}
