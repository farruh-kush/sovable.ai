"""Gateway Service configuration.

All settings are loaded from environment variables, with sensible defaults
for local development. Production values are injected via Docker / Kubernetes
secrets.

Author: Farruh
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Environment-driven settings for the API Gateway Service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")

    # Downstream service URLs (resolved via Docker Compose / K8s service names)
    auth_service_url: str = Field(
        default="http://auth:8001", alias="AUTH_SERVICE_URL"
    )
    router_service_url: str = Field(
        default="http://router:8002", alias="ROUTER_SERVICE_URL"
    )
    billing_service_url: str = Field(
        default="http://billing:8004", alias="BILLING_SERVICE_URL"
    )

    # Redis (for rate limiting — Phase 1 Task 1.1)
    redis_url: str = Field(
        default="redis://redis:6379/0", alias="REDIS_URL"
    )

    # Admin key for management endpoints
    admin_api_key: str = Field(default="change-me-in-production", alias="ADMIN_API_KEY")


@lru_cache
def get_settings() -> GatewaySettings:
    """Return a cached settings instance."""
    return GatewaySettings()
