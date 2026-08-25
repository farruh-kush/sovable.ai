"""Router Engine Service configuration.

Author: Farruh
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RouterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    redis_url: str = Field(default="redis://redis:6379/1", alias="REDIS_URL")
    routing_config_path: str = Field(
        default="/app/config/routing.yaml", alias="ROUTING_CONFIG_PATH"
    )
    provider_service_url: str = Field(default="http://provider:8003", alias="PROVIDER_SERVICE_URL")
    billing_service_url: str = Field(default="http://billing:8004", alias="BILLING_SERVICE_URL")

    # Latency tracking TTL in seconds (Phase 4 — Task 4.1)
    latency_ttl_seconds: int = Field(default=300, alias="LATENCY_TTL_SECONDS")

    # Prompt cache TTL in seconds (Phase 3 — Task 3.2)
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")


@lru_cache
def get_settings() -> RouterSettings:
    return RouterSettings()
