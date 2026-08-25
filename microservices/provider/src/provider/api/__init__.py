"""Provider Adapter Service API routes.

Author: Farruh
"""

from __future__ import annotations

from ai_routing_shared.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from ai_routing_shared.utils import get_logger
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def adapt_chat(body: dict, request: Request) -> ChatCompletionResponse | StreamingResponse:
    """Adapt a chat completion request to the specified provider."""
    provider_name = body.pop("_provider", None)
    if not provider_name:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Missing '_provider' field.")

    chat_request = ChatCompletionRequest.model_validate(body)
    adapter = request.app.state.registry.get(provider_name)

    if chat_request.stream:

        async def event_generator():
            async for chunk in adapter.chat_stream(chat_request):
                yield f"data: {chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return await adapter.chat(chat_request)


@router.post("/embeddings", response_model=EmbeddingResponse)
async def adapt_embeddings(body: dict, request: Request) -> EmbeddingResponse:
    """Adapt an embedding request to the specified provider."""
    provider_name = body.pop("_provider", None)
    if not provider_name:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Missing '_provider' field.")

    embed_request = EmbeddingRequest.model_validate(body)
    adapter = request.app.state.registry.get(provider_name)
    return await adapter.embeddings(embed_request)


@router.get("/health")
async def health(request: Request) -> dict:
    """Return health status of all registered providers."""
    adapters = request.app.state.registry.all()
    return {
        "status": "healthy",
        "service": "provider",
        "providers": {
            name: {
                "configured": bool(adapter.api_key),
                "circuit_open": not adapter.health.is_available(),
                "error_count": adapter.health.error_count,
                "last_latency_ms": adapter.health.last_latency_ms,
            }
            for name, adapter in adapters.items()
        },
    }
