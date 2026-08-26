"""Deterministic policy evaluation for route selection."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field

from router.core.catalog import CatalogDocument


@dataclass(frozen=True)
class RouteContext:
    correlation_id: str
    tenant_id: str = "unknown"
    user_id: str = "unknown"
    tier: str = "pro"
    region: str | None = None
    compliance: frozenset[str] = frozenset()
    capabilities: frozenset[str] = frozenset({"chat"})
    modality: str = "text"
    streaming: bool = False
    estimated_cost_usd: float = 0.0
    cost_cap_usd: float | None = None
    explicit_provider_order: tuple[str, ...] = ()
    allow_fallbacks: bool = True


@dataclass(frozen=True)
class ProviderHealthSignal:
    circuit_open: bool = False
    error_rate_5m: float = 0.0
    p95_latency_ms: float = 0.0
    inflight: int = 0


@dataclass(frozen=True)
class RouteDecision:
    decision_id: str
    correlation_id: str
    requested_model: str
    selected_model: str
    selected_provider: str
    candidates: tuple[str, ...]
    rejected: dict[str, tuple[str, ...]] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()
    strategy: str = "static"
    experiment_id: str | None = None
    variant: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "correlation_id": self.correlation_id,
            "requested_model": self.requested_model,
            "selected_model": self.selected_model,
            "selected_provider": self.selected_provider,
            "candidates": list(self.candidates),
            "rejected": {key: list(value) for key, value in self.rejected.items()},
            "reasons": list(self.reasons),
            "strategy": self.strategy,
            "experiment_id": self.experiment_id,
            "variant": self.variant,
        }


class NoRoute(Exception):
    def __init__(self, message: str, rejected: dict[str, tuple[str, ...]]):
        super().__init__(message)
        self.rejected = rejected


class PolicyEvaluator:
    """Evaluate only pure inputs; no provider call can bypass hard constraints."""

    def __init__(
        self,
        catalog: CatalogDocument,
        health: dict[str, ProviderHealthSignal] | None = None,
    ):
        self.catalog = catalog
        self.health = health or {}

    def decide(self, model: str, context: RouteContext) -> RouteDecision:
        if model in self.catalog.deny_list:
            raise NoRoute(f"model {model!r} is deny-listed", {model: ("deny_list",)})

        selected_model, strategy, candidates = self._resolve_model_and_candidates(model)
        rejected: dict[str, tuple[str, ...]] = {}
        viable: list[str] = []
        for provider in candidates:
            reasons = self._hard_rejections(selected_model, provider, context)
            if reasons:
                rejected[provider] = tuple(reasons)
            else:
                viable.append(provider)

        if context.explicit_provider_order:
            order = {
                name: idx for idx, name in enumerate(context.explicit_provider_order)
            }
            viable.sort(
                key=lambda provider: (
                    order.get(provider, len(order)),
                    candidates.index(provider),
                )
            )
            strategy = "explicit_order"

        experiment_id, variant = self._experiment(context, viable)
        if variant and variant in viable:
            viable.remove(variant)
            viable.insert(0, variant)
            strategy = "experiment"

        viable = self._score(viable, selected_model, strategy)
        if not viable:
            raise NoRoute(f"no provider satisfies policy for {model!r}", rejected)

        concrete_model = self._model_for_provider(model, viable[0])
        decision_id = hashlib.sha256(
            f"{context.correlation_id}:{context.tenant_id}:{model}:{viable[0]}:{self.catalog.policy_version}".encode()
        ).hexdigest()[:24]
        reasons = [
            f"policy_version={self.catalog.policy_version}",
            f"strategy={strategy}",
        ]
        reasons.extend(f"candidate={provider}" for provider in viable)
        if experiment_id:
            reasons.append(f"experiment={experiment_id}:{variant}")
        return RouteDecision(
            decision_id=f"route_{decision_id}",
            correlation_id=context.correlation_id,
            requested_model=model,
            selected_model=concrete_model,
            selected_provider=viable[0],
            candidates=tuple(viable),
            rejected=rejected,
            reasons=tuple(reasons),
            strategy=strategy,
            experiment_id=experiment_id,
            variant=variant,
        )

    def _resolve_model_and_candidates(
        self, requested_model: str
    ) -> tuple[str, str, list[str]]:
        alias = self.catalog.aliases.get(requested_model)
        if alias and alias.get("kind") == "strategy":
            candidates: list[str] = []
            for candidate_model in alias.get("candidates", []):
                entry = self.catalog.models.get(candidate_model)
                if entry and entry.provider not in candidates:
                    candidates.append(entry.provider)
            return requested_model, str(alias.get("strategy", "static")), candidates
        route = self.catalog.routing.get(requested_model)
        if route:
            candidates = [
                provider for provider in [route.primary, *route.fallback] if provider
            ]
            return requested_model, route.strategy, list(dict.fromkeys(candidates))
        model_entry = self.catalog.models.get(requested_model)
        if model_entry:
            return requested_model, "static", [model_entry.provider]
        return requested_model, "static", list(self.catalog.providers)

    def _hard_rejections(
        self, model: str, provider: str, context: RouteContext
    ) -> list[str]:
        provider_entry = self.catalog.providers.get(provider)
        model_entry = self.catalog.models.get(model)
        if provider_entry is None:
            return ["provider_missing_from_catalog"]
        reasons: list[str] = []
        if (
            not provider_entry.availability.enabled
            and provider_entry.availability.status not in {"healthy", "degraded"}
        ):
            reasons.append(f"provider_{provider_entry.availability.status}")
        if context.region and context.region not in provider_entry.regions:
            reasons.append("region_not_allowed")
        if model_entry and context.region and context.region not in model_entry.regions:
            reasons.append("model_region_not_allowed")
        required = set(context.compliance)
        tags = set(provider_entry.compliance_tags)
        if "gdpr" in required and "gdpr" not in tags:
            reasons.append("gdpr_required")
        if ({"zero_data_retention", "no_training"} & required) and (
            not provider_entry.data_policy.zero_data_retention
            or provider_entry.data_policy.trains_on_data
        ):
            reasons.append("zero_data_retention_required")
        if "eu_residency" in required and "eu_residency" not in tags:
            reasons.append("eu_residency_required")
        if "self_hosted" in required and "self_hosted" not in tags:
            reasons.append("self_hosted_required")
        if context.streaming and "streaming" not in provider_entry.capabilities:
            reasons.append("streaming_unsupported")
        if context.capabilities - set(provider_entry.capabilities):
            reasons.append("capability_unsupported")
        if context.modality == "image" and "vision" not in provider_entry.capabilities:
            reasons.append("image_modality_unsupported")
        health = self.health.get(
            provider,
            ProviderHealthSignal(
                circuit_open=provider_entry.health.circuit_open,
                error_rate_5m=provider_entry.health.error_rate_5m,
                p95_latency_ms=provider_entry.health.p95_latency_ms,
            ),
        )
        if health.circuit_open:
            reasons.append("circuit_open")
        if health.error_rate_5m >= 0.5:
            reasons.append("provider_error_rate_high")
        if (
            context.cost_cap_usd is not None
            and context.estimated_cost_usd > context.cost_cap_usd
        ):
            reasons.append("cost_cap_exceeded")
        return reasons

    def _score(self, candidates: list[str], model: str, strategy: str) -> list[str]:
        if strategy == "cost":
            return sorted(
                candidates, key=lambda p: (self._cost(p, model), candidates.index(p))
            )
        if strategy == "latency":
            return sorted(
                candidates,
                key=lambda p: (
                    self._health(p).p95_latency_ms or float("inf"),
                    candidates.index(p),
                ),
            )
        if strategy == "quality":
            rank = {"frontier": 0, "standard": 1, "economy": 2}
            return sorted(
                candidates,
                key=lambda p: (
                    rank.get(self._quality_for(p, model), 3),
                    candidates.index(p),
                ),
            )
        return candidates

    def _model_for_provider(self, model: str, provider: str) -> str:
        alias = self.catalog.aliases.get(model)
        if alias and alias.get("kind") == "strategy":
            for candidate_model in alias.get("candidates", []):
                entry = self.catalog.models.get(str(candidate_model))
                if entry and entry.provider == provider:
                    return str(candidate_model)
        return model

    def _cost(self, provider: str, model: str) -> float:
        model = self._model_for_provider(model, provider)
        entry = self.catalog.models.get(model)
        if entry and entry.provider == provider:
            pricing = entry.pricing_usd_per_million_tokens
            return pricing.input + pricing.output
        return 10_000.0

    def _quality_for(self, provider: str, model: str) -> str:
        model = self._model_for_provider(model, provider)
        entry = self.catalog.models.get(model)
        return entry.quality_tier if entry and entry.provider == provider else "economy"

    def _health(self, provider: str) -> ProviderHealthSignal:
        return self.health.get(provider, ProviderHealthSignal())

    def _experiment(
        self, context: RouteContext, viable: Iterable[str]
    ) -> tuple[str | None, str | None]:
        for experiment in self.catalog.experiments:
            if experiment.get(
                "status"
            ) != "active" or context.tier not in experiment.get("eligible_tiers", []):
                continue
            variants = [
                str(v) for v in experiment.get("variants", []) if str(v) in viable
            ]
            if not variants or int(experiment.get("traffic_percent", 0)) <= 0:
                continue
            digest = (
                hashlib.sha256(
                    f"{experiment.get('salt', experiment.get('id', ''))}:{context.tenant_id}".encode()
                ).digest()[0]
                % 100
            )
            if digest < int(experiment["traffic_percent"]):
                return str(experiment.get("id")), variants[digest % len(variants)]
        return None, None
