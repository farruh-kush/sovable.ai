"""API key management endpoints — /v1/keys.

Author: Farruh
"""

from __future__ import annotations

import httpx
from ai_routing_shared.models import ApiKeyTier
from ai_routing_shared.utils import get_logger
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ...core.config import GatewaySettings, get_settings

router = APIRouter()
logger = get_logger(__name__)


class CreateKeyRequest(BaseModel):
    name: str
    tier: ApiKeyTier = ApiKeyTier.FREE
    monthly_budget_usd: float | None = None
    allowed_models: list[str] | None = None


@router.post("/keys")
async def create_key(
    body: CreateKeyRequest,
    x_admin_key: str | None = Header(default=None),
    settings: GatewaySettings = Depends(get_settings),
) -> dict:
    """Create a new API key (admin-only endpoint)."""
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    async with httpx.AsyncClient(base_url=settings.auth_service_url, timeout=10.0) as client:
        response = await client.post("/internal/keys", json=body.model_dump())
        response.raise_for_status()

    return response.json()


@router.get("/keys")
async def list_keys(
    x_admin_key: str | None = Header(default=None),
    settings: GatewaySettings = Depends(get_settings),
) -> dict:
    """List all API keys (admin-only endpoint)."""
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    async with httpx.AsyncClient(base_url=settings.auth_service_url, timeout=10.0) as client:
        response = await client.get("/internal/keys")
        response.raise_for_status()

    return response.json()
