"""Privacy masking preview endpoint."""

from __future__ import annotations

from typing import Any

import httpx
from ai_routing_shared.models import ApiKey
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ...core.auth import enforce_rate_limit
from ...core.config import GatewaySettings, get_settings
from ...core.downstream import request_peer, response_error_or_none, response_json

router = APIRouter()


@router.post("/privacy/preview", response_model=None)
async def privacy_preview(
    body: dict[str, Any],
    request: Request,
    api_key: ApiKey = Depends(enforce_rate_limit),
    settings: GatewaySettings = Depends(get_settings),
) -> dict[str, Any] | JSONResponse:
    """Preview masking for an authenticated API-key principal."""
    payload = dict(body)
    payload.update({"_api_key_id": api_key.id, "_user_id": api_key.user_id})
    headers = {"x-request-id": request.headers["x-request-id"]} if request.headers.get("x-request-id") else {}
    async with httpx.AsyncClient(
        base_url=settings.router_service_url,
        timeout=httpx.Timeout(20.0, connect=5.0),
    ) as client:
        response = await request_peer(
            client,
            "POST",
            "/route/privacy/preview",
            service="router",
            json=payload,
            headers=headers,
        )
    mapped = response_error_or_none(response, "router")
    if mapped is not None:
        return mapped
    result = response_json(response, "router")
    return result if isinstance(result, dict) else {"data": result}
