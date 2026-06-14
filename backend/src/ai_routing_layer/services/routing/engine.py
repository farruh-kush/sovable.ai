from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ai_routing_layer.providers.base import BaseProvider, ProviderRegistry


@dataclass
class RouteDecision:
    primary: str
    fallbacks: list[str]


class RoutingEngine:
    def __init__(self, registry: ProviderRegistry, config_path: Path) -> None:
        self.registry = registry
        self.config_path = config_path
        self._config = self._load_config(config_path)

    @staticmethod
    def _load_config(config_path: Path) -> dict:
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        return {}

    def decision_for_model(self, model: str) -> RouteDecision:
        routing = self._config.get("routing", {}).get(model)
        if routing:
            return RouteDecision(primary=routing["primary"], fallbacks=routing.get("fallback", []))
        available = [provider.name for provider in self.registry.all()]
        if not available:
            raise ValueError("No providers registered")
        return RouteDecision(primary=available[0], fallbacks=available[1:])

    def candidates_for_model(self, model: str) -> list[BaseProvider]:
        decision = self.decision_for_model(model)
        names = [decision.primary, *decision.fallbacks]
        # Collect available providers (preserve order from routing decision)
        providers = [
            self.registry.get(name) for name in names if self.registry.get(name).health.available()
        ]
        # Some test/dummy providers may not implement `api_key`; prefer providers with keys but keep others as fallbacks
        providers = sorted(providers, key=lambda p: bool(getattr(p, "api_key", None)), reverse=True)
        if not providers:
            providers = [self.registry.get(name) for name in names]
            providers = sorted(
                providers, key=lambda p: bool(getattr(p, "api_key", None)), reverse=True
            )
        return self._rank_dynamic(model, providers)

    def _rank_dynamic(self, model: str, providers: list[BaseProvider]) -> list[BaseProvider]:
        dynamic = self._config.get("dynamic_routing", {})
        if not dynamic.get("enabled", False):
            return providers
        cost_weight = float(dynamic.get("cost_weight", 0.4))
        latency_weight = float(dynamic.get("latency_weight", 0.3))
        availability_weight = float(dynamic.get("availability_weight", 0.3))
        configured_order = {provider.name: index for index, provider in enumerate(providers)}

        def score(provider: BaseProvider) -> float:
            if model.startswith("gpt"):
                cost_hint = 1.0 if provider.name == "openai" else 0.4
            elif model.startswith("claude"):
                cost_hint = 1.0 if provider.name == "anthropic" else 0.4
            else:
                cost_hint = 0.7
            availability = 1.0 if provider.health.available() else 0.0
            latency_component = 1 / max(provider.health.last_latency_ms, 1.0)
            order_bias = max(0.0, 1.0 - configured_order.get(provider.name, 0) * 0.05)
            return (
                cost_hint * cost_weight
                + latency_component * latency_weight * 100
                + availability * availability_weight
                + order_bias
            )

        return sorted(providers, key=score, reverse=True)
