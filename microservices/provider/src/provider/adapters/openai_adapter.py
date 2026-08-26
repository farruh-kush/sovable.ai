"""OpenAI provider adapter."""
from __future__ import annotations
from typing import Any, Optional
from .openai_compatible import OpenAICompatibleAdapter

_OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAIAdapter(OpenAICompatibleAdapter):
    name = "openai"
    default_base_url = _OPENAI_BASE_URL
    allowed_hosts = frozenset({"api.openai.com", "api.manus.im"})

    def __init__(self, api_key: Optional[str], timeout_seconds: float = 30.0, base_url: str = _OPENAI_BASE_URL, mock_mode: bool = True, **kwargs: Any) -> None:
        super().__init__(api_key, timeout_seconds, base_url=base_url, mock_mode=mock_mode, **kwargs)
