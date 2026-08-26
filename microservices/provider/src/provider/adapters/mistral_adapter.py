"""Mistral provider adapter."""
from __future__ import annotations
from typing import Any, Optional
from .openai_compatible import OpenAICompatibleAdapter

_MISTRAL_BASE_URL = "https://api.mistral.ai/v1"


class MistralAdapter(OpenAICompatibleAdapter):
    name = "mistral"
    default_base_url = _MISTRAL_BASE_URL
    allowed_hosts = frozenset({"api.mistral.ai"})

    def __init__(self, api_key: Optional[str], timeout_seconds: float = 30.0, mock_mode: bool = True, **kwargs: Any) -> None:
        super().__init__(api_key, timeout_seconds, base_url=_MISTRAL_BASE_URL, mock_mode=mock_mode, **kwargs)
