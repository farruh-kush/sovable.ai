from pathlib import Path

from ai_routing_layer.providers import AnthropicProvider, OpenAIProvider, ProviderRegistry
from ai_routing_layer.router import RoutingEngine


def test_static_routing_and_fallback_order() -> None:
    registry = ProviderRegistry([OpenAIProvider(api_key=None), AnthropicProvider(api_key=None)])
    engine = RoutingEngine(registry, Path("config/routing.yaml"))
    candidates = engine.candidates_for_model("gpt-4o-mini")
    assert candidates[0].name == "openai"
    assert {provider.name for provider in candidates} == {"openai", "anthropic"}


def test_dynamic_routing_prefers_available_provider() -> None:
    registry = ProviderRegistry([OpenAIProvider(api_key=None), AnthropicProvider(api_key=None)])
    registry.get("openai").health.circuit_open_until = 10**12
    engine = RoutingEngine(registry, Path("config/routing.yaml"))
    candidates = engine.candidates_for_model("gpt-4o-mini")
    assert candidates[0].name == "anthropic"
