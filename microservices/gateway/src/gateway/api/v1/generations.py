"""Activity Logs API — /v1/generations.

Phase 3 — Task 3.3: Exposes per-request generation metadata including
provider, token breakdown, cost, and cache status.

Author: Farruh
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends

from ai_routing_shared.models import ApiKey, GenerationRecord
from ai_routing_shared.exceptions import AuthorisationError

from ...core.auth import get_api_key
from ...core.config import GatewaySettings, get_settings

router = APIRouter()


@router.get("/generations/{generation_id}", response_model=GenerationRecord)
async def get_generation(
    generation_id: str,
    api_key: ApiKey = Depends(get_api_key),
    settings: GatewaySettings = Depends(get_settings),
) -> GenerationRecord:
    """Retrieve detailed metadata for a specific generation.

    Users can only retrieve their own generations. The ``generation_id``
    is returned in the ``X-Generation-Id`` response header of every
    chat completion request.
    """
    async with httpx.AsyncClient(
        base_url=settings.billing_service_url, timeout=10.0
    ) as client:
        response = await client.get(
            f"/internal/generations/{generation_id}",
            params={"user_id": api_key.user_id},
        )

    if response.status_code == 403:
        raise AuthorisationError("You do not have access to this generation record.")

    response.raise_for_status()
    return GenerationRecord.model_validate(response.json())
