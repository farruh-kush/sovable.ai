"""Versioned REST boundary for Gateway and Router."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ai_routing_shared.exceptions import AuthenticationError
from ai_routing_shared.models import ChatCompletionRequest, ChatCompletionResponse, EmbeddingRequest, EmbeddingResponse
from ai_routing_shared.utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _provider_body(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    provider = str(body.get("_provider") or body.get("provider") or "").strip().lower()
    if not provider:
        raise AuthenticationError("Provider selection is required.", details={"field": "_provider"})
    payload = dict(body)
    payload.pop("_provider", None)
    # `provider` is a routing preference object in the public request contract;
    # do not pass it through as a provider selector.
    if isinstance(payload.get("provider"), str):
        payload.pop("provider", None)
    return provider, payload


def _correlation_id(request: Request) -> str:
    return request.headers.get("x-correlation-id") or request.headers.get("x-request-id") or "provider-local"


async def _sse(adapter: Any, chat_request: ChatCompletionRequest, correlation_id: str) -> AsyncIterator[str]:
    try:
        async for chunk in adapter.chat_stream(chat_request):
            yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    except Exception:
        logger.warning("provider_stream_failed", correlation_id=correlation_id, provider=adapter.name)
        raise


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def adapt_chat(body: dict[str, Any], request: Request) -> ChatCompletionResponse | StreamingResponse:
    provider_name, payload = _provider_body(body)
    correlation_id = _correlation_id(request)
    chat_request = ChatCompletionRequest.model_validate(payload)
    adapter = request.app.state.registry.get(provider_name)
    logger.info("provider_chat_start", correlation_id=correlation_id, provider=provider_name, model=chat_request.model, stream=chat_request.stream)
    if chat_request.stream:
        return StreamingResponse(_sse(adapter, chat_request, correlation_id), media_type="text/event-stream", headers={"x-correlation-id": correlation_id, "cache-control": "no-cache"})
    return await adapter.chat(chat_request)


@router.post("/embeddings", response_model=EmbeddingResponse)
async def adapt_embeddings(body: dict[str, Any], request: Request) -> EmbeddingResponse:
    provider_name, payload = _provider_body(body)
    correlation_id = _correlation_id(request)
    embed_request = EmbeddingRequest.model_validate(payload)
    adapter = request.app.state.registry.get(provider_name)
    logger.info("provider_embedding_start", correlation_id=correlation_id, provider=provider_name, model=embed_request.model)
    return await adapter.embeddings(embed_request)


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    adapters = request.app.state.registry.all()
    providers = {name: (await adapter.health_check()).model_dump(mode="json") for name, adapter in adapters.items()}
    return {"status": "healthy" if all(item["healthy"] or item["signal"] == "unconfigured" for item in providers.values()) else "degraded", "service": "provider", "version": "v1", "providers": providers}


@router.get("/capabilities")
async def capabilities(request: Request) -> dict[str, Any]:
    adapters = request.app.state.registry.all()
    return {"version": "v1", "providers": {name: (await adapter.discover_capabilities()).model_dump(mode="json") for name, adapter in adapters.items()}}
