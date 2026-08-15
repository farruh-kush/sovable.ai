"""Canonical Pydantic domain models for the AI Routing Layer.

All microservices import from this module to guarantee a consistent
request/response contract across service boundaries.

Author: Farruh
"""

from .requests import (
    ChatCompletionRequest,
    EmbeddingRequest,
    ProviderPreferences,
    ChatMessage,
)
from .responses import (
    ChatCompletionResponse,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ChatChoice,
    EmbeddingResponse,
    EmbeddingVector,
)
from .usage import UsageInfo, UsageRecord, GenerationRecord, GenerationCost
from .keys import ApiKey, ApiKeyTier

__all__ = [
    # Requests
    "ChatCompletionRequest",
    "EmbeddingRequest",
    "ProviderPreferences",
    "ChatMessage",
    # Responses
    "ChatCompletionResponse",
    "ChatCompletionChunk",
    "ChatCompletionChunkChoice",
    "ChatCompletionChunkDelta",
    "ChatChoice",
    "EmbeddingResponse",
    "EmbeddingVector",
    # Usage
    "UsageInfo",
    "UsageRecord",
    "GenerationRecord",
    "GenerationCost",
    # Keys
    "ApiKey",
    "ApiKeyTier",
]
