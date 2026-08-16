"""Authenticated privacy preview proxy. Author: Farruh"""
from __future__ import annotations
from typing import Any
import httpx
from fastapi import APIRouter, Depends, Request
from ai_routing_shared.models import ApiKey
from ...core.auth import enforce_rate_limit
from ...core.config import GatewaySettings, get_settings

router = APIRouter()

@router.post("/privacy/preview")
async def privacy_preview(
    body: dict[str, Any],
    request: Request,
    api_key: ApiKey = Depends(enforce_rate_limit),
    settings: GatewaySettings = Depends(get_settings),
) -> dict[str, Any]:
    """Preview masking for an authenticated API-key principal."""
    payload = dict(body)
    payload["_api_key_id"] = api_key.id
    payload["_user_id"] = api_key.user_id
    async with httpx.AsyncClient(base_url=settings.router_service_url, timeout=20.0) as client:
        response = await client.post("/route/privacy/preview", json=payload)
        response.raise_for_status()
    return response.json()
