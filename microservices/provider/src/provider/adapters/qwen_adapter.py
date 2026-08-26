"""Alibaba Model Studio / Qwen adapter.

Model Studio's compatible-mode endpoint is deliberately isolated behind this
adapter so endpoint changes do not leak into Gateway or Router contracts.
"""
from __future__ import annotations
from typing import Any, Optional
from .openai_compatible import OpenAICompatibleAdapter

_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class AlibabaQwenAdapter(OpenAICompatibleAdapter):
    name = "alibaba"
    default_base_url = _DASHSCOPE_BASE_URL
    allowed_hosts = frozenset({"dashscope.aliyuncs.com"})

    def __init__(self, api_key: Optional[str], timeout_seconds: float = 30.0, base_url: str = _DASHSCOPE_BASE_URL, mock_mode: bool = True, **kwargs: Any) -> None:
        super().__init__(api_key, timeout_seconds, base_url=base_url, mock_mode=mock_mode, **kwargs)


QwenAdapter = AlibabaQwenAdapter

__all__ = ["AlibabaQwenAdapter", "QwenAdapter"]
