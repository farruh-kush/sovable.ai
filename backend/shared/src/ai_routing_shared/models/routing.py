"""Typed contracts for routing control-plane and observability interfaces."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RouteDecisionContract(BaseModel):
    decision_id: str
    correlation_id: str
    requested_model: str
    selected_model: str
    selected_provider: str
    candidates: list[str]
    rejected: dict[str, list[str]] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    strategy: str
    experiment_id: str | None = None
    variant: str | None = None


class CatalogEnvelope(BaseModel):
    catalog: dict[str, Any]
    checksum: str


class ProviderHealthContract(BaseModel):
    status: str
    enabled: bool
    circuit_open: bool
    error_rate_5m: float = Field(ge=0, le=1)
    p95_latency_ms: float = Field(ge=0)


class HealthEnvelope(BaseModel):
    catalog_version: str
    policy_version: str
    checksum: str
    providers: dict[str, ProviderHealthContract]


class RoutingSummaryContract(BaseModel):
    catalog_version: str
    policy_version: str
    checksum: str
    precedence: list[str]
    policies: list[dict[str, Any]]
    providers: list[str]
    model_count: int = Field(ge=0)
