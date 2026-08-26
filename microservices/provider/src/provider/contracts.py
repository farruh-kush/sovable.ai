"""Versioned provider-adapter domain contracts.

The provider service owns these contracts and exposes them only through the
versioned HTTP facade. They intentionally contain no provider credentials or
raw prompt logging fields.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Capability(StrEnum):
    CHAT = "chat"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    TOOLS = "tools"
    JSON_MODE = "json_mode"
    VISION = "vision"
    SYSTEM_MESSAGES = "system_messages"


class UsageSource(StrEnum):
    MEASURED = "measured"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class ErrorClass(StrEnum):
    AUTHENTICATION = "authentication"
    AUTHORISATION = "authorisation"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    MALFORMED_RESPONSE = "malformed_response"
    NETWORK = "network"
    CIRCUIT_OPEN = "circuit_open"
    CANCELLED = "cancelled"
    CONFIGURATION = "configuration"


class ProviderMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    provider: str
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    supports: set[Capability] = Field(default_factory=set)


class CapabilitySet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    configured: bool
    capabilities: set[Capability] = Field(default_factory=set)
    models: list[ProviderMetadata] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    source: UsageSource = UsageSource.UNAVAILABLE


class ProviderCost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Literal["USD"] = "USD"
    amount: float = Field(default=0.0, ge=0.0)
    input_amount: float = Field(default=0.0, ge=0.0)
    output_amount: float = Field(default=0.0, ge=0.0)
    source: Literal["provider_metadata", "local_price_table", "unavailable"] = "unavailable"


class HealthResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    configured: bool
    healthy: bool
    circuit_open: bool
    last_latency_ms: float = 0.0
    consecutive_failures: int = 0
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signal: Literal["ready", "unconfigured", "circuit_open", "degraded"]


class ProviderErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    classification: ErrorClass
    retryable: bool
    correlation_id: str
    provider_request_id: str | None = None
    retry_after_seconds: float | None = None
    message: str = "Provider request failed."


class AdapterRequestContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    deadline_at: datetime | None = None
    tenant_id_hash: str | None = None
    idempotency_key: str | None = None


class NormalizedRequest(BaseModel):
    """Provider-neutral request envelope used by adapter implementations."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    model: str
    messages_or_input: Any
    generation_parameters: dict[str, Any] = Field(default_factory=dict)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    response_format: dict[str, Any] | None = None
    stream: bool = False
    timeout_ms: int = Field(default=30_000, ge=1, le=120_000)
    deadline_at: datetime | None = None
    policy_context: dict[str, Any] = Field(default_factory=dict)


class NormalizedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    model: str
    provider: str
    output: Any
    finish_reason: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    cost: ProviderCost = Field(default_factory=ProviderCost)
    provider_request_id: str | None = None
    latency_ms: int = 0


class NormalizedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    model: str
    provider: str
    delta: str | None = None
    role: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    provider_request_id: str | None = None


def calculate_cost(metadata: ProviderMetadata | None, usage: TokenUsage) -> ProviderCost:
    """Calculate local cost without retaining request content."""
    if metadata is None or metadata.input_cost_per_million is None or metadata.output_cost_per_million is None:
        return ProviderCost()
    input_amount = usage.input_tokens * metadata.input_cost_per_million / 1_000_000
    output_amount = usage.output_tokens * metadata.output_cost_per_million / 1_000_000
    return ProviderCost(
        amount=round(input_amount + output_amount, 10),
        input_amount=round(input_amount, 10),
        output_amount=round(output_amount, 10),
        source="local_price_table",
    )


__all__ = [
    "AdapterRequestContext",
    "Capability",
    "CapabilitySet",
    "ErrorClass",
    "HealthResult",
    "NormalizedChunk",
    "NormalizedRequest",
    "NormalizedResponse",
    "ProviderCost",
    "ProviderErrorBody",
    "ProviderMetadata",
    "TokenUsage",
    "UsageSource",
    "calculate_cost",
]
