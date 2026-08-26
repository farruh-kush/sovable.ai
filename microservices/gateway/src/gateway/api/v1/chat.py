"""OpenAI-compatible chat completions endpoint."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from ai_routing_shared.exceptions import UpstreamServiceError, UpstreamTimeoutError
from ai_routing_shared.models import ApiKey, ChatCompletionRequest, ChatCompletionResponse
from ai_routing_shared.utils import get_logger
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from ...core.auth import enforce_budget, enforce_model_whitelist
from ...core.config import GatewaySettings, get_settings
from ...core.downstream import request_peer, response_error_or_none, response_json

router = APIRouter()
logger = get_logger(__name__)


def _compute_cache_key(request: ChatCompletionRequest) -> str:
    """Return a deterministic key for all response-affecting request fields."""
    payload = request.model_dump(exclude={"stream"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _sse_error(code: str, message: str) -> str:
    return f"data: {json.dumps({'error': {'code': code, 'message': message}})}\n\ndata: [DONE]\n\n"


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    api_key: ApiKey = Depends(enforce_budget),
    settings: GatewaySettings = Depends(get_settings),
) -> ChatCompletionResponse | JSONResponse | StreamingResponse:
    """Validate, authorize, and forward a chat completion request to Router."""
    enforce_model_whitelist(body.model, api_key)
    redis = request.app.state.redis
    cache_key = _compute_cache_key(body)

    if not body.stream:
        cached = await redis.get_cached_response(cache_key)
        if cached:
            try:
                response = ChatCompletionResponse.model_validate(json.loads(cached))
            except (ValueError, ValidationError):
                logger.warning("cache_entry_invalid", model=body.model)
            else:
                logger.info("cache_hit", model=body.model, api_key_id=api_key.id)
                content = response.model_dump()
                content["cache_hit"] = True
                json_response = JSONResponse(content=content)
                json_response.headers["X-Cache"] = "HIT"
                if response.generation_id:
                    json_response.headers["X-Generation-Id"] = response.generation_id
                return json_response

    router_payload = body.model_dump()
    router_payload.update({"_api_key_id": api_key.id, "_user_id": api_key.user_id})

    if body.stream:
        return await _stream_from_router(router_payload, settings, request)

    timeout = httpx.Timeout(120.0, connect=5.0)
    async with httpx.AsyncClient(base_url=settings.router_service_url, timeout=timeout) as client:
        response = await request_peer(
            client,
            "POST",
            "/route/chat/completions",
            service="router",
            json=router_payload,
            headers=_request_headers(request),
        )
    mapped = response_error_or_none(response, "router")
    if mapped is not None:
        return mapped

    try:
        result = ChatCompletionResponse.model_validate(response_json(response, "router"))
    except ValidationError as exc:
        raise UpstreamServiceError(
            "Router service returned an invalid completion.",
            service="router",
            details={"service": "router"},
        ) from exc

    await redis.set_cached_response(cache_key, result.model_dump_json())
    logger.info(
        "completion_forwarded",
        model=result.model,
        provider=result.provider,
        api_key_id=api_key.id,
        generation_id=result.generation_id,
    )
    json_response = JSONResponse(content=result.model_dump())
    json_response.headers["X-Cache"] = "MISS"
    if result.generation_id:
        json_response.headers["X-Generation-Id"] = result.generation_id
    return json_response


def _request_headers(request: Request) -> dict[str, str]:
    request_id = request.headers.get("x-request-id")
    return {"x-request-id": request_id} if request_id else {}


async def _stream_from_router(
    payload: dict[str, Any], settings: GatewaySettings, request: Request | None = None
) -> StreamingResponse | JSONResponse:
    """Open and proxy Router SSE without leaking upstream exceptions."""
    client = httpx.AsyncClient(
        base_url=settings.router_service_url,
        timeout=httpx.Timeout(120.0, connect=5.0),
    )
    try:
        outbound = client.build_request(
            "POST",
            "/route/chat/completions",
            json=payload,
            headers=_request_headers(request) if request else {},
        )
        response = await client.send(outbound, stream=True)
    except httpx.TimeoutException as exc:
        await client.aclose()
        raise UpstreamTimeoutError(
            "Router service timed out.",
            service="router",
            details={"service": "router"},
        ) from exc
    except httpx.RequestError as exc:
        await client.aclose()
        raise UpstreamServiceError(
            "Router service is temporarily unavailable.",
            service="router",
            details={"service": "router"},
        ) from exc

    if response.status_code >= 400:
        await response.aread()
        await response.aclose()
        await client.aclose()
        mapped = response_error_or_none(response, "router")
        if mapped is not None:
            return mapped

    async def event_generator():
        try:
            async for line in response.aiter_lines():
                if line:
                    yield f"{line}\n\n"
        except httpx.TimeoutException:
            logger.warning("router_stream_timeout")
            yield _sse_error("upstream_timeout", "Router service timed out.")
        except httpx.RequestError:
            logger.warning("router_stream_unreachable")
            yield _sse_error("upstream_service_error", "Router service is unavailable.")
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
