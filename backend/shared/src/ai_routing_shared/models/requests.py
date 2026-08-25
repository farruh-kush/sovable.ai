"""Request schemas for the AI Routing Layer.

These models are the canonical input contracts for the API Gateway.
The ``ProviderPreferences`` object implements the client-side routing
controls described in Phase 3 / Task 3.1 of the implementation plan.

Author: Farruh
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]]


class ProviderPreferences(BaseModel):
    """Client-side routing controls (Phase 3 — Task 3.1).

    Allows clients to dictate the routing strategy on a per-request basis,
    mirroring OpenRouter's ``provider`` object.

    Attributes:
        sort: Optimisation axis — ``"price"``, ``"throughput"``, or ``"latency"``.
        order: Ordered list of provider slugs to try (e.g. ``["anthropic", "openai"]``).
        allow_fallbacks: When ``False``, the request fails if the first provider
            is unavailable rather than falling back to the next in the chain.
        data_collection: Set to ``"deny"`` to exclude providers that may train
            on user data or do not offer Zero Data Retention (ZDR).
    """

    sort: Literal["price", "throughput", "latency"] | None = None
    order: list[str] | None = None
    allow_fallbacks: bool = True
    data_collection: Literal["allow", "deny"] | None = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request.

    Extended with ``provider`` preferences for intelligent routing.
    """

    model: str
    messages: list[ChatMessage]
    temperature: float | None = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False
    user: str | None = None
    metadata: dict[str, Any] | None = None

    # Phase 3 — Task 3.1: Client-side routing controls
    provider: ProviderPreferences | None = None

    # Phase 3 — Task 3.4: Data policy routing
    response_format: dict[str, Any] | None = None


class EmbeddingRequest(BaseModel):
    """OpenAI-compatible embedding request."""

    model: str
    input: str | list[str]
    user: str | None = None
