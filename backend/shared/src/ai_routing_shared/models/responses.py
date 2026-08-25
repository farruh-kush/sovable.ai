"""Response schemas for the AI Routing Layer.

All provider adapters normalise their outputs into these models, guaranteeing
that the same request always produces the same response shape regardless of
which upstream provider fulfilled it.

Author: Farruh
"""

from __future__ import annotations

from pydantic import BaseModel

from .requests import ChatMessage  # single canonical definition
from .usage import UsageInfo


class ChatChoice(BaseModel):
    """A single completion choice."""

    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatCompletionResponse(BaseModel):
    """Normalised chat completion response (OpenAI-compatible)."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    provider: str
    choices: list[ChatChoice]
    usage: UsageInfo

    # Phase 3 — Task 3.2: Prompt caching metadata
    cache_hit: bool = False

    # Phase 3 — Task 3.3: Activity log reference
    generation_id: str | None = None


class ChatCompletionChunkDelta(BaseModel):
    """Delta content for a streaming chunk."""

    role: str | None = None
    content: str | None = None


class ChatCompletionChunkChoice(BaseModel):
    """A single choice within a streaming chunk."""

    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    """A single Server-Sent Event chunk for streaming responses."""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    provider: str
    choices: list[ChatCompletionChunkChoice]


class EmbeddingVector(BaseModel):
    """A single embedding vector."""

    object: str = "embedding"
    index: int
    embedding: list[float]


class EmbeddingResponse(BaseModel):
    """Normalised embedding response."""

    object: str = "list"
    data: list[EmbeddingVector]
    model: str
    provider: str
    usage: UsageInfo
