"""Typed, validated, and atomically reloadable routing catalog."""

from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class Availability(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    status: Literal["healthy", "degraded", "unconfigured", "disabled", "deprecated"] = (
        "healthy"
    )
    reason: str | None = None


class HealthSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    circuit_open: bool = False
    error_rate_5m: float = Field(default=0.0, ge=0.0, le=1.0)
    p95_latency_ms: float = Field(default=0.0, ge=0.0)


class DataPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trains_on_data: bool = False
    zero_data_retention: bool = False
    retention_days: int = Field(default=0, ge=0)


class ProviderCatalog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display_name: str
    adapter: str
    api_key_env: str
    base_url_env: str | None = None
    regions: list[str] = Field(min_length=1)
    compliance_tags: list[str] = Field(default_factory=list)
    data_policy: DataPolicy = Field(default_factory=DataPolicy)
    capabilities: list[str] = Field(default_factory=list)
    availability: Availability = Field(default_factory=Availability)
    health: HealthSnapshot = Field(default_factory=HealthSnapshot)
    default_timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)


class PricingSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    input: float = Field(ge=0)
    output: float = Field(ge=0)
    currency: str = "USD"
    effective_at: str | None = None


class Deprecation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Literal["active", "deprecated", "sunset"] = "active"
    sunset_at: str | None = None
    replacement: str | None = None


class ModelCatalog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    provider: str
    model_name: str
    family: str
    kind: Literal["chat", "embedding"]
    context_window: int = Field(gt=0)
    max_output_tokens: int = Field(ge=0)
    dimensions: int | None = Field(default=None, gt=0)
    modalities: list[str] = Field(min_length=1)
    capability_tags: list[str] = Field(default_factory=list)
    regions: list[str] = Field(min_length=1)
    compliance_tags: list[str] = Field(default_factory=list)
    quality_tier: Literal["frontier", "standard", "economy"]
    availability: Literal["active", "configurable", "disabled", "deprecated"]
    pricing_usd_per_million_tokens: PricingSnapshot
    deprecation: Deprecation = Field(default_factory=Deprecation)

    @field_validator("dimensions")
    @classmethod
    def embeddings_need_dimensions(cls, value: int | None, info: Any) -> int | None:
        if info.data.get("kind") == "embedding" and value is None:
            raise ValueError("embedding models require dimensions")
        return value


class RoutingEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    strategy: Literal["static", "cost", "latency", "quality", "throughput"] = "static"
    primary: str | None = None
    fallback: list[str] = Field(default_factory=list)
    candidates: list[str] = Field(default_factory=list)


class TierPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    allowed_models: list[str] | Literal["*"] = "*"
    requests_per_minute: int = Field(default=60, gt=0)
    requests_per_day: int = Field(default=1000, gt=0)
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    allow_streaming: bool = True
    allow_fallbacks: bool = True
    enable_ab_testing: bool = False
    require_zero_data_retention: bool = False


class ReloadPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mode: Literal["atomic_snapshot"] = "atomic_snapshot"
    poll_interval_seconds: int = Field(default=30, gt=0)
    require_schema_validation: bool = True
    retain_previous_on_error: bool = True
    audit_event: str = "routing_policy_reload"


class CatalogDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schema_version: str
    catalog_version: str
    policy_version: str
    status: Literal["active", "paused", "retired"] = "active"
    reload: ReloadPolicy = Field(default_factory=ReloadPolicy)
    providers: dict[str, ProviderCatalog] = Field(min_length=1)
    models: dict[str, ModelCatalog] = Field(min_length=1)
    aliases: dict[str, dict[str, Any]] = Field(default_factory=dict)
    routing: dict[str, RoutingEntry] = Field(default_factory=dict)
    tier_policies: dict[str, TierPolicy] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    pricing: dict[str, Any] = Field(default_factory=dict)
    experiments: list[dict[str, Any]] = Field(default_factory=list)
    observability: dict[str, Any] = Field(default_factory=dict)
    deny_list: list[str] = Field(default_factory=list)

    @field_validator("models")
    @classmethod
    def model_providers_must_exist(
        cls, value: dict[str, ModelCatalog], info: Any
    ) -> dict[str, ModelCatalog]:
        providers = info.data.get("providers", {})
        unknown = sorted(
            {
                model.provider
                for model in value.values()
                if model.provider not in providers
            }
        )
        if unknown:
            raise ValueError(f"models reference unknown providers: {unknown}")
        return value

    @field_validator("routing")
    @classmethod
    def routing_providers_must_exist(
        cls, value: dict[str, RoutingEntry], info: Any
    ) -> dict[str, RoutingEntry]:
        providers = info.data.get("providers", {})
        for alias, route in value.items():
            unknown = [
                p
                for p in [route.primary, *route.fallback, *route.candidates]
                if p and p not in providers
            ]
            if unknown:
                raise ValueError(
                    f"routing entry {alias!r} references unknown providers: {sorted(set(unknown))}"
                )
        return value


class CatalogError(ValueError):
    """Raised when a catalog cannot be loaded or validated."""


class CatalogManager:
    """Keep the last valid catalog and swap it atomically on safe reload."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._catalog: CatalogDocument | None = None
        self._checksum: str | None = None
        self._load_initial()

    def _load_initial(self) -> None:
        catalog, checksum = self._parse_file()
        with self._lock:
            self._catalog, self._checksum = catalog, checksum

    def _parse_file(self) -> tuple[CatalogDocument, str]:
        try:
            raw = self.path.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
            document = CatalogDocument.model_validate(yaml.safe_load(raw) or {})
        except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
            raise CatalogError(f"invalid routing catalog: {exc}") from exc
        forbidden = {"api_key", "token", "secret", "authorization", "password"}
        if any(
            any(word in str(key).lower() for word in forbidden)
            for key in document.model_dump()
        ):
            raise CatalogError("routing catalog contains a forbidden credential field")
        return document, checksum

    def reload_if_changed(self) -> bool:
        with self._lock:
            current_checksum = self._checksum
        try:
            raw = self.path.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
        except OSError:
            return False
        if checksum == current_checksum:
            return False
        try:
            document, checksum = self._parse_file()
        except CatalogError:
            return False
        with self._lock:
            self._catalog, self._checksum = document, checksum
        return True

    def snapshot(self) -> CatalogDocument:
        with self._lock:
            if self._catalog is None:
                raise CatalogError("catalog is not loaded")
            return self._catalog.model_copy(deep=True)

    @property
    def checksum(self) -> str:
        with self._lock:
            return self._checksum or ""

    def redacted_snapshot(self) -> dict[str, Any]:
        data = self.snapshot().model_dump(mode="json")
        for provider in data.get("providers", {}).values():
            provider.pop("api_key_env", None)
            provider.pop("base_url_env", None)
        return data


def catalog_path_from_env(default: str = "/app/config/routing.yaml") -> Path:
    return Path(os.getenv("ROUTING_CONFIG_PATH", default))
