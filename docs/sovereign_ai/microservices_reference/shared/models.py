from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: dict[str, Any]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Any
    name: str | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    model: str = "local"
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class Principal(BaseModel):
    api_key_id: str
    subject: str
    organization_id: str
    tier: Literal["free", "paid", "admin"]
    scopes: list[str] = Field(default_factory=list)


class AuthorizeRequest(BaseModel):
    api_key: str
    required_scope: str = "chat:complete"


class AuthorizeResponse(BaseModel):
    principal: Principal


class RouteRequest(BaseModel):
    request_id: str
    requested_model: str
    principal: Principal
    allow_external: bool = False
    estimated_tokens: int = 0


class RouteDecision(BaseModel):
    provider: str
    provider_model: str
    endpoint: str
    fallback_chain: list[str] = Field(default_factory=list)
    reason: str
    unit_cost_usd_per_1k: float = 0.0
    estimated_cost_usd: float = 0.0


class ProviderChatRequest(BaseModel):
    request_id: str
    route: RouteDecision
    chat: ChatRequest


class ProviderChatResponse(BaseModel):
    response: dict[str, Any]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost_usd: float


class QuotaCheckRequest(BaseModel):
    principal: Principal
    estimated_cost_usd: float = 0.0


class QuotaCheckResponse(BaseModel):
    allowed: bool
    monthly_cost_usd: float
    monthly_budget_usd: float
    reason: str | None = None


class UsageEvent(BaseModel):
    request_id: str
    principal: Principal
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost_usd: float


class UsageReceipt(BaseModel):
    request_id: str
    recorded: bool
    total_cost_usd: float
    monthly_cost_usd: float
    alert: str | None = None


class HealthResponse(BaseModel):
    service: str
    status: Literal["ok"]
