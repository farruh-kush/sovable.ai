"""Response schemas for the AI Routing Layer.

All provider adapters normalise their outputs into these models, guaranteeing
that the same request always produces the same response shape regardless of
which upstream provider fulfilled it.

Author: Farruh
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .usage import UsageInfo


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str
    content: str


class ChatChoice(BaseModel):
    """A single completion choice."""

    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """Normalised chat completion response (OpenAI-compatible)."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    provider: str
    choices: List[ChatChoice]
    usage: UsageInfo

    # Phase 3 — Task 3.2: Prompt caching metadata
    cache_hit: bool = False

    # Phase 3 — Task 3.3: Activity log reference
    generation_id: Optional[str] = None


class ChatCompletionChunkDelta(BaseModel):
    """Delta content for a streaming chunk."""

    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionChunkChoice(BaseModel):
    """A single choice within a streaming chunk."""

    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """A single Server-Sent Event chunk for streaming responses."""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    provider: str
    choices: List[ChatCompletionChunkChoice]


class EmbeddingVector(BaseModel):
    """A single embedding vector."""

    object: str = "embedding"
    index: int
    embedding: List[float]


class EmbeddingResponse(BaseModel):
    """Normalised embedding response."""

    object: str = "list"
    data: List[EmbeddingVector]
    model: str
    provider: str
    usage: UsageInfo
