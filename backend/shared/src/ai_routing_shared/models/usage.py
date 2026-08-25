"""Usage and billing domain models.

These models are shared between the Router Engine (which produces usage events)
and the Billing Service (which consumes and persists them).

Author: Farruh
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class UsageInfo(BaseModel):
    """Token usage metadata attached to every completion response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Phase 3 — Task 3.2: Prompt caching enrichment
    cached_tokens: int = 0
    cache_discount_usd: float = 0.0
    cache_hit: bool = False


class UsageRecord(BaseModel):
    """A persisted record of a single API call.

    Written asynchronously by the Router Engine and consumed by the Billing
    Service for cost tracking, quota enforcement, and the activity logs API.
    """

    id: str = Field(default_factory=lambda: f"gen_{uuid4().hex}")
    api_key_id: str
    user_id: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    markup_usd: float
    billed_usd: float
    latency_ms: float
    fallback_used: bool = False
    cache_hit: bool = False
    cached_tokens: int = 0
    cache_discount_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Phase 4 — Task 4.3: A/B testing
    experiment_name: str | None = None
    experiment_variant: str | None = None

    # Phase 4 — Task 4.4: Structured output validation
    schema_validation_passed: bool | None = None
    validation_retry_count: int = 0


class GenerationRecord(BaseModel):
    """Public-facing generation detail (Phase 3 — Task 3.3: /v1/generations).

    Returned by ``GET /v1/generations/{generation_id}``.
    """

    id: str
    model: str
    provider: str
    created_at: datetime
    usage: UsageInfo
    cost: GenerationCost
    latency_ms: float
    fallback_used: bool
    cache_hit: bool


class GenerationCost(BaseModel):
    """Detailed cost breakdown for a single generation."""

    prompt_cost_usd: float
    completion_cost_usd: float
    cache_discount_usd: float
    total_cost_usd: float
    markup_usd: float
    billed_usd: float
