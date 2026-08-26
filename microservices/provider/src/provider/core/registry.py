"""Provider adapter registry and lifecycle management."""
from __future__ import annotations

from typing import Dict

from ai_routing_shared.exceptions import AuthorisationError, NoProvidersAvailableError
from ai_routing_shared.utils import get_logger

from ..adapters.anthropic_adapter import AnthropicAdapter
from ..adapters.base import BaseProviderAdapter, RetryPolicy
from ..adapters.google_adapter import GoogleAdapter
from ..adapters.mistral_adapter import MistralAdapter
from ..adapters.openai_adapter import OpenAIAdapter
from ..adapters.qwen_adapter import AlibabaQwenAdapter
from .config import ProviderSettings

logger = get_logger(__name__)


class ProviderRegistry:
    """Owns adapter instances; it does not access any service database."""

    def __init__(self, settings: ProviderSettings) -> None:
        self._allowlist = settings.provider_allowlist
        policy = RetryPolicy(max_attempts=settings.retry_max_attempts)
        common = {"timeout_seconds": settings.default_timeout_seconds, "mock_mode": settings.mock_mode, "max_concurrency": settings.max_concurrency, "retry_policy": policy}
        self._adapters: Dict[str, BaseProviderAdapter] = {
            "openai": OpenAIAdapter(settings.openai_api_key, base_url=settings.openai_base_url, **common),
            "anthropic": AnthropicAdapter(settings.anthropic_api_key, **common),
            "google": GoogleAdapter(settings.google_api_key, **common),
            "mistral": MistralAdapter(settings.mistral_api_key, **common),
            "alibaba": AlibabaQwenAdapter(settings.dashscope_api_key or settings.qwen_api_key, **common),
        }
        # Compatibility alias for clients that called the provider qwen.
        self._adapters["qwen"] = self._adapters["alibaba"]
        logger.info("providers_registered", provider_names=sorted(self._adapters), configured_names=sorted(name for name, adapter in self._adapters.items() if adapter.configured))

    def get(self, name: str) -> BaseProviderAdapter:
        normalized = name.strip().lower()
        adapter = self._adapters.get(normalized)
        if adapter is None:
            raise NoProvidersAvailableError("No adapter is registered for the requested provider.", details={"provider": normalized})
        if normalized not in self._allowlist:
            raise AuthorisationError("Provider selection is not permitted.", details={"provider": normalized})
        return adapter

    def all(self) -> Dict[str, BaseProviderAdapter]:
        return dict(self._adapters)

    async def aclose(self) -> None:
        unique = {id(adapter): adapter for adapter in self._adapters.values()}
        for adapter in unique.values():
            await adapter.aclose()
