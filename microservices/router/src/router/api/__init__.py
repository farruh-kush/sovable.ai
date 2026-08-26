"""Router Engine Service API routes.
Author: Farruh
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ai_routing_shared.models import (
    CatalogEnvelope,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthEnvelope,
    RouteDecisionContract,
    RoutingSummaryContract,
)
from ai_routing_shared.privacy import mask_chat_messages
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


def _correlation_id(request: Request) -> str | None:
    return request.headers.get("X-Request-Id") or request.headers.get(
        "X-Correlation-Id"
    )


def _restore_response(
    response: ChatCompletionResponse, session: Any
) -> ChatCompletionResponse:
    """Restore request-local tokens only in the normalized client response."""
    payload = response.model_dump()
    for choice in payload.get("choices", []):
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = session.restore_text(content)
    return ChatCompletionResponse.model_validate(payload)


async def _restore_stream(
    chunks: AsyncIterator[str], session: Any
) -> AsyncIterator[str]:
    """Restore tokens in normalized SSE chunks without exposing raw values upstream."""
    async for chunk in chunks:
        yield session.restore_text(chunk)


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def route_chat(
    body: dict[str, Any], request: Request
) -> ChatCompletionResponse | StreamingResponse:
    """Route chat through request-local masking before the provider boundary."""
    api_key_id = body.pop("_api_key_id", "unknown")
    user_id = body.pop("_user_id", "unknown")
    chat_request = ChatCompletionRequest.model_validate(body)
    masked_messages, masking_session = mask_chat_messages(chat_request.messages)
    masked_request = chat_request.model_copy(update={"messages": masked_messages})
    engine = request.app.state.routing_engine
    if masked_request.stream:
        return StreamingResponse(
            _restore_stream(
                engine.route_chat_stream(
                    masked_request, api_key_id, user_id, _correlation_id(request)
                ),
                masking_session,
            ),
            media_type="text/event-stream",
        )
    response = await engine.route_chat_completion(
        request=masked_request,
        api_key_id=api_key_id,
        user_id=user_id,
        correlation_id=_correlation_id(request),
    )
    return _restore_response(response, masking_session)


@router.post("/embeddings", response_model=EmbeddingResponse)
async def route_embeddings(body: dict[str, Any], request: Request) -> EmbeddingResponse:
    """Route an embedding request to the optimal provider."""
    api_key_id = body.pop("_api_key_id", "unknown")
    user_id = body.pop("_user_id", "unknown")
    embed_request = EmbeddingRequest.model_validate(body)
    return await request.app.state.routing_engine.route_embedding(
        request=embed_request,
        api_key_id=api_key_id,
        user_id=user_id,
        correlation_id=_correlation_id(request),
    )


@router.post("/privacy/preview")
async def privacy_preview(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """Preview masking without returning any original sensitive values."""
    messages = [
        ChatMessage.model_validate(item) for item in (body.get("messages") or [])
    ]
    masked_messages, session = mask_chat_messages(messages)
    return {
        "masked_messages": [message.model_dump() for message in masked_messages],
        "detected_count": len(session.mapping),
        "token_labels": [token.split("_")[1] for token in session.mapping],
        "restoration": "request-local; original values are not returned by this endpoint",
        "provider_boundary": (
            "masked content is sent upstream and restored only in normalized client output"
        ),
    }


@router.get("/models")
async def list_models(request: Request) -> dict:
    """Return available models with provider and data policy metadata."""
    return request.app.state.routing_engine.get_models()


@router.get("/catalog", response_model=CatalogEnvelope)
async def catalog(request: Request) -> dict:
    """Return the validated, secret-free catalog snapshot."""
    return request.app.state.routing_engine.get_catalog()


@router.get("/health", response_model=HealthEnvelope)
async def routing_health(request: Request) -> dict:
    """Return catalog and provider health signals without credentials."""
    return request.app.state.routing_engine.get_health()


@router.get("/routing/summary", response_model=RoutingSummaryContract)
async def routing_summary(request: Request) -> dict:
    """Return a safe summary of routing policy configuration."""
    return request.app.state.routing_engine.get_routing_summary()


@router.get("/routing/decisions/{correlation_id}", response_model=RouteDecisionContract)
async def route_decision(correlation_id: str, request: Request) -> dict:
    """Return an auditable route decision retained for this process."""
    decision = request.app.state.routing_engine.get_last_decision(correlation_id)
    if decision is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="route decision not found")
    return decision
