"""Provider Registry.

Instantiates and manages all configured provider adapters.

Author: Farruh
"""

from __future__ import annotations

from ai_routing_shared.exceptions import NoProvidersAvailableError
from ai_routing_shared.utils import get_logger

from ..adapters.anthropic_adapter import AnthropicAdapter
from ..adapters.base import BaseProviderAdapter
from ..adapters.google_adapter import GoogleAdapter
from ..adapters.mistral_adapter import MistralAdapter
from ..adapters.openai_adapter import OpenAIAdapter
from .config import ProviderSettings

logger = get_logger(__name__)


class ProviderRegistry:
    """Registry of all available provider adapters."""

    def __init__(self, settings: ProviderSettings) -> None:
        self._adapters: dict[str, BaseProviderAdapter] = {}
        self._register_all(settings)

    def _register_all(self, settings: ProviderSettings) -> None:
        """Instantiate all configured adapters."""
        self._adapters["openai"] = OpenAIAdapter(
            api_key=settings.openai_api_key,
            timeout_seconds=settings.default_timeout_seconds,
            base_url=settings.openai_base_url,
        )
        self._adapters["anthropic"] = AnthropicAdapter(
            api_key=settings.anthropic_api_key,
            timeout_seconds=settings.default_timeout_seconds,
        )
        self._adapters["google"] = GoogleAdapter(
            api_key=settings.google_api_key,
            timeout_seconds=settings.default_timeout_seconds,
        )
        self._adapters["mistral"] = MistralAdapter(
            api_key=settings.mistral_api_key,
            timeout_seconds=settings.default_timeout_seconds,
        )
        logger.info(
            "providers_registered",
            providers=list(self._adapters.keys()),
            configured=[k for k, v in self._adapters.items() if v.api_key],
        )

    def get(self, name: str) -> BaseProviderAdapter:
        """Return the adapter for the given provider name."""
        adapter = self._adapters.get(name)
        if adapter is None:
            raise NoProvidersAvailableError(
                f"No adapter registered for provider '{name}'.",
                details={"available": list(self._adapters.keys())},
            )
        return adapter

    def all(self) -> dict[str, BaseProviderAdapter]:
        """Return all registered adapters."""
        return dict(self._adapters)
