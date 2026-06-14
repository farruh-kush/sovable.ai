from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

from ai_routing_layer.auth.rate_limit import RateLimiter
from ai_routing_layer.billing.service import BillingService, PricingCatalog, UsageStore
from ai_routing_layer.config import get_settings
from ai_routing_layer.observability.metrics import MetricsRegistry
from ai_routing_layer.providers import AnthropicProvider, OpenAIProvider, ProviderRegistry
from ai_routing_layer.router import RoutingEngine
from ai_routing_layer.service import RoutingService


@dataclass
class AppContainer:
    provider_registry: ProviderRegistry
    router: RoutingEngine
    rate_limiter: RateLimiter
    billing_service: BillingService
    metrics: MetricsRegistry
    routing_service: RoutingService

    _instance: ClassVar[Optional["AppContainer"]] = None

    @classmethod
    def build(cls) -> "AppContainer":
        settings = get_settings()
        provider_registry = ProviderRegistry(
            [
                OpenAIProvider(
                    api_key=settings.openai_api_key,
                    timeout_seconds=settings.default_timeout_seconds,
                ),
                AnthropicProvider(
                    api_key=settings.anthropic_api_key,
                    timeout_seconds=settings.default_timeout_seconds,
                ),
            ]
        )
        billing_service = BillingService(PricingCatalog(), UsageStore())
        metrics = MetricsRegistry()
        router = RoutingEngine(provider_registry, settings.routing_config_path)
        routing_service = RoutingService(router=router, billing=billing_service, metrics=metrics)
        return cls(
            provider_registry=provider_registry,
            router=router,
            rate_limiter=RateLimiter(),
            billing_service=billing_service,
            metrics=metrics,
            routing_service=routing_service,
        )

    @classmethod
    def instance(cls) -> "AppContainer":
        if cls._instance is None:
            cls._instance = cls.build()
        return cls._instance
