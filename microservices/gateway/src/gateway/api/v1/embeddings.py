"""Embeddings endpoint — /v1/embeddings.

Author: Farruh
"""

from __future__ import annotations

import httpx
from ai_routing_shared.models import ApiKey, EmbeddingRequest, EmbeddingResponse
from fastapi import APIRouter, Depends, Request

from ...core.auth import enforce_budget, enforce_model_whitelist
from ...core.config import GatewaySettings, get_settings

router = APIRouter()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embeddings(
    body: EmbeddingRequest,
    request: Request,
    api_key: ApiKey = Depends(enforce_budget),
    settings: GatewaySettings = Depends(get_settings),
) -> EmbeddingResponse:
    """Handle embedding requests."""
    enforce_model_whitelist(body.model, api_key)

    payload = body.model_dump()
    payload["_api_key_id"] = api_key.id
    payload["_user_id"] = api_key.user_id

    async with httpx.AsyncClient(base_url=settings.router_service_url, timeout=60.0) as client:
        response = await client.post("/route/embeddings", json=payload)
        response.raise_for_status()

    return EmbeddingResponse.model_validate(response.json())
