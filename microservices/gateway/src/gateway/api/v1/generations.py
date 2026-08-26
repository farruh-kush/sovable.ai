"""Generation metadata proxy endpoint."""

from __future__ import annotations

import httpx
from ai_routing_shared.exceptions import AuthorisationError, UpstreamServiceError
from ai_routing_shared.models import ApiKey, GenerationRecord
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ...core.auth import get_api_key
from ...core.config import GatewaySettings, get_settings
from ...core.downstream import request_peer, response_error_or_none, response_json

router = APIRouter()


@router.get("/generations/{generation_id}", response_model=GenerationRecord)
async def get_generation(
    generation_id: str,
    request: Request,
    api_key: ApiKey = Depends(get_api_key),
    settings: GatewaySettings = Depends(get_settings),
) -> GenerationRecord | JSONResponse:
    """Retrieve detailed metadata for a generation owned by the caller."""
    headers = {"x-request-id": request.headers["x-request-id"]} if request.headers.get("x-request-id") else {}
    async with httpx.AsyncClient(
        base_url=settings.billing_service_url,
        timeout=httpx.Timeout(10.0, connect=3.0),
    ) as client:
        response = await request_peer(
            client,
            "GET",
            f"/internal/generations/{generation_id}",
            service="billing",
            params={"user_id": api_key.user_id},
            headers=headers,
        )

    if response.status_code == 403:
        raise AuthorisationError("You do not have access to this generation record.")
    mapped = response_error_or_none(response, "billing")
    if mapped is not None:
        return mapped
    try:
        return GenerationRecord.model_validate(response_json(response, "billing"))
    except ValidationError as exc:
        raise UpstreamServiceError(
            "Billing service returned an invalid generation record.",
            service="billing",
            details={"service": "billing"},
        ) from exc
