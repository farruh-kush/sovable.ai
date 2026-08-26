"""Model catalogue proxy endpoint."""

from __future__ import annotations

import httpx
from ai_routing_shared.models import ApiKey
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ...core.auth import get_api_key
from ...core.config import GatewaySettings, get_settings
from ...core.downstream import request_peer, response_error_or_none, response_json

router = APIRouter()


@router.get("/models", response_model=None)
async def list_models(
    request: Request,
    api_key: ApiKey = Depends(get_api_key),
    settings: GatewaySettings = Depends(get_settings),
) -> dict | JSONResponse:
    """Return the Router-owned model catalogue."""
    headers = {"x-request-id": request.headers["x-request-id"]} if request.headers.get("x-request-id") else {}
    async with httpx.AsyncClient(
        base_url=settings.router_service_url,
        timeout=httpx.Timeout(10.0, connect=3.0),
    ) as client:
        response = await request_peer(
            client,
            "GET",
            "/route/models",
            service="router",
            headers=headers,
        )
    mapped = response_error_or_none(response, "router")
    if mapped is not None:
        return mapped
    payload = response_json(response, "router")
    return payload if isinstance(payload, dict) else {"data": payload}
