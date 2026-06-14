"""Provider Adapter Service configuration.

Author: Farruh
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_timeout_seconds: float = Field(default=30.0, alias="DEFAULT_TIMEOUT_SECONDS")

    # Provider API keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    mistral_api_key: Optional[str] = Field(default=None, alias="MISTRAL_API_KEY")


@lru_cache
def get_settings() -> ProviderSettings:
    return ProviderSettings()
