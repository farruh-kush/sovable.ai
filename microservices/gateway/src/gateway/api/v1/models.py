"""Models listing endpoint — /v1/models.

Author: Farruh
"""

from __future__ import annotations

import httpx
from ai_routing_shared.models import ApiKey
from fastapi import APIRouter, Depends

from ...core.auth import get_api_key
from ...core.config import GatewaySettings, get_settings

router = APIRouter()


@router.get("/models")
async def list_models(
    api_key: ApiKey = Depends(get_api_key),
    settings: GatewaySettings = Depends(get_settings),
) -> dict:
    """Return the list of available models and their provider metadata.

    Phase 3 — Task 3.4: Includes data policy tags per provider.
    """
    async with httpx.AsyncClient(base_url=settings.router_service_url, timeout=10.0) as client:
        response = await client.get("/route/models")
        response.raise_for_status()

    return response.json()
