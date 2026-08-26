"""Provider service configuration.

Deployments should inject secret values from Kubernetes Secrets as environment
variables. The adapter layer never reads files, databases, or request payloads
for credentials.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_timeout_seconds: float = Field(default=30.0, alias="DEFAULT_TIMEOUT_SECONDS", ge=0.1, le=120.0)
    retry_max_attempts: int = Field(default=3, alias="PROVIDER_RETRY_MAX_ATTEMPTS", ge=1, le=5)
    circuit_failure_threshold: int = Field(default=3, alias="PROVIDER_CIRCUIT_FAILURE_THRESHOLD", ge=1, le=20)
    circuit_open_seconds: float = Field(default=30.0, alias="PROVIDER_CIRCUIT_OPEN_SECONDS", ge=1.0, le=600.0)
    max_concurrency: int = Field(default=32, alias="PROVIDER_MAX_CONCURRENCY", ge=1, le=256)
    mock_mode: bool = Field(default=True, alias="PROVIDER_MOCK_MODE")
    allowed_provider_names: str = Field(default="openai,anthropic,google,mistral,alibaba,qwen", alias="PROVIDER_ALLOWLIST")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    mistral_api_key: Optional[str] = Field(default=None, alias="MISTRAL_API_KEY")
    dashscope_api_key: Optional[str] = Field(default=None, alias="DASHSCOPE_API_KEY")
    qwen_api_key: Optional[str] = Field(default=None, alias="QWEN_API_KEY")

    @property
    def provider_allowlist(self) -> frozenset[str]:
        return frozenset(item.strip().lower() for item in self.allowed_provider_names.split(",") if item.strip())


@lru_cache(maxsize=1)
def get_settings() -> ProviderSettings:
    return ProviderSettings()
