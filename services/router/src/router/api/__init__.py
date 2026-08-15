"""Router Engine Service API routes.

Author: Farruh
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ai_routing_shared.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)

router = APIRouter()


class _InternalChatRequest(ChatCompletionRequest):
    """Extended request that carries internal routing metadata."""
    _api_key_id: str = ""
    _user_id: str = ""


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def route_chat(
    body: dict,
    request: Request,
) -> ChatCompletionResponse:
    """Route a chat completion request to the optimal provider."""
    api_key_id = body.pop("_api_key_id", "unknown")
    user_id = body.pop("_user_id", "unknown")
    chat_request = ChatCompletionRequest.model_validate(body)

    engine = request.app.state.routing_engine
    if chat_request.stream:
        return StreamingResponse(
            engine.route_chat_stream(chat_request, api_key_id, user_id),
            media_type="text/event-stream",
        )
    return await engine.route_chat_completion(
        request=chat_request,
        api_key_id=api_key_id,
        user_id=user_id,
    )


@router.post("/embeddings", response_model=EmbeddingResponse)
async def route_embeddings(
    body: dict,
    request: Request,
) -> EmbeddingResponse:
    """Route an embedding request to the optimal provider."""
    api_key_id = body.pop("_api_key_id", "unknown")
    user_id = body.pop("_user_id", "unknown")
    embed_request = EmbeddingRequest.model_validate(body)

    return await request.app.state.routing_engine.route_embedding(
        request=embed_request,
        api_key_id=api_key_id,
        user_id=user_id,
    )


@router.get("/models")
async def list_models(request: Request) -> dict:
    """Return available models with provider and data policy metadata."""
    return request.app.state.routing_engine.get_models()
