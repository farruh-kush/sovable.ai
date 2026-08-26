"""Canonical Pydantic domain models for the AI Routing Layer.

All microservices import from this module to guarantee a consistent
request/response contract across service boundaries.

Author: Farruh
"""

from .keys import ApiKey, ApiKeyTier
from .requests import (
    ChatCompletionRequest,
    ChatMessage,
    EmbeddingRequest,
    ProviderPreferences,
)
from .responses import (
    ChatChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ChatCompletionResponse,
    EmbeddingResponse,
    EmbeddingVector,
)
from .usage import GenerationCost, GenerationRecord, UsageInfo, UsageRecord
from .routing import (
    CatalogEnvelope,
    HealthEnvelope,
    ProviderHealthContract,
    RouteDecisionContract,
    RoutingSummaryContract,
)

__all__ = [
    "ApiKey",
    "ApiKeyTier",
    "ChatChoice",
    "ChatCompletionChunk",
    "ChatCompletionChunkChoice",
    "ChatCompletionChunkDelta",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "EmbeddingVector",
    "GenerationCost",
    "GenerationRecord",
    "ProviderPreferences",
    "UsageInfo",
    "UsageRecord",
    "CatalogEnvelope",
    "HealthEnvelope",
    "ProviderHealthContract",
    "RouteDecisionContract",
    "RoutingSummaryContract",
]
