"""OpenAI-compatible embeddings endpoint."""

from __future__ import annotations

import httpx
from ai_routing_shared.exceptions import UpstreamServiceError
from ai_routing_shared.models import ApiKey, EmbeddingRequest, EmbeddingResponse
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ...core.auth import enforce_budget, enforce_model_whitelist
from ...core.config import GatewaySettings, get_settings
from ...core.downstream import request_peer, response_error_or_none, response_json

router = APIRouter()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embeddings(
    body: EmbeddingRequest,
    request: Request,
    api_key: ApiKey = Depends(enforce_budget),
    settings: GatewaySettings = Depends(get_settings),
) -> EmbeddingResponse | JSONResponse:
    """Validate and forward an embedding request to Router."""
    enforce_model_whitelist(body.model, api_key)
    payload = body.model_dump()
    payload.update({"_api_key_id": api_key.id, "_user_id": api_key.user_id})

    async with httpx.AsyncClient(
        base_url=settings.router_service_url,
        timeout=httpx.Timeout(60.0, connect=5.0),
    ) as client:
        response = await request_peer(
            client,
            "POST",
            "/route/embeddings",
            service="router",
            json=payload,
            headers={"x-request-id": request.headers["x-request-id"]}
            if request.headers.get("x-request-id")
            else {},
        )
    mapped = response_error_or_none(response, "router")
    if mapped is not None:
        return mapped

    try:
        return EmbeddingResponse.model_validate(response_json(response, "router"))
    except ValidationError as exc:
        raise UpstreamServiceError(
            "Router service returned an invalid embedding response.",
            service="router",
            details={"service": "router"},
        ) from exc
