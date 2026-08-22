"""Chat completions endpoint — /v1/chat/completions.

This is the primary endpoint of the AI Routing Layer, implementing the
OpenAI-compatible chat completions API. All Phase 1 policy enforcement
(rate limiting, budget caps, model whitelists) occurs here before the
request is forwarded to the Router Engine Service.

Author: Farruh
"""

from __future__ import annotations

import hashlib
import json

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ai_routing_shared.models import ApiKey, ChatCompletionRequest, ChatCompletionResponse
from ai_routing_shared.utils import get_logger

from ...core.auth import enforce_budget, enforce_model_whitelist
from ...core.config import GatewaySettings, get_settings

router = APIRouter()
logger = get_logger(__name__)


def _compute_cache_key(request: ChatCompletionRequest) -> str:
    """Compute a deterministic cache key for prompt-level caching.

    Phase 3 — Task 3.2: The key is derived from the model, messages,
    temperature, and max_tokens so that semantically identical requests
    share a cache entry.
    """
    payload = {
        "model": request.model,
        "messages": [m.model_dump() for m in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    api_key: ApiKey = Depends(enforce_budget),
    settings: GatewaySettings = Depends(get_settings),
) -> ChatCompletionResponse | StreamingResponse:
    """Handle chat completion requests.

    Applies all Phase 1 policy checks before forwarding to the Router:
    1. Rate limiting (enforced by ``enforce_budget`` dependency chain)
    2. Monthly budget cap (enforced by ``enforce_budget``)
    3. Model whitelist (enforced inline below)

    Then checks the gateway-level prompt cache (Phase 3 — Task 3.2)
    before forwarding to the Router Engine Service.
    """
    # Phase 1 — Task 1.3: Model whitelist check
    enforce_model_whitelist(body.model, api_key)

    redis = request.app.state.redis

    # Phase 3 — Task 3.2: Gateway-level prompt cache check
    if not body.stream:
        cache_key = _compute_cache_key(body)
        cached = await redis.get_cached_response(cache_key)
        if cached:
            logger.info("cache_hit", model=body.model, api_key_id=api_key.id)
            response_data = json.loads(cached)
            response_data["cache_hit"] = True
            response = ChatCompletionResponse.model_validate(response_data)
            # Return with cache header
            from fastapi.responses import JSONResponse
            content = response.model_dump()
            json_response = JSONResponse(content=content)
            json_response.headers["X-Cache"] = "HIT"
            return json_response

    # Forward to Router Engine Service
    router_payload = body.model_dump()
    router_payload["_api_key_id"] = api_key.id
    router_payload["_user_id"] = api_key.user_id

    if body.stream:
        return await _stream_from_router(router_payload, settings)

    async with httpx.AsyncClient(
        base_url=settings.router_service_url, timeout=120.0
    ) as client:
        response = await client.post("/route/chat/completions", json=router_payload)
        response.raise_for_status()
        result = ChatCompletionResponse.model_validate(response.json())

    # Phase 3 — Task 3.2: Store in gateway cache on miss
    if not body.stream:
        await redis.set_cached_response(cache_key, result.model_dump_json())

    from fastapi.responses import JSONResponse
    json_response = JSONResponse(content=result.model_dump())
    json_response.headers["X-Cache"] = "MISS"
    if result.generation_id:
        json_response.headers["X-Generation-Id"] = result.generation_id
    return json_response


async def _stream_from_router(
    payload: dict, settings: GatewaySettings
) -> StreamingResponse:
    """Proxy a streaming response from the Router Engine Service."""

    async def event_generator():
        async with httpx.AsyncClient(
            base_url=settings.router_service_url, timeout=120.0
        ) as client:
            async with client.stream(
                "POST", "/route/chat/completions", json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
