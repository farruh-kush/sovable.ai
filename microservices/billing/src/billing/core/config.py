"""Billing Service configuration.

Author: Farruh
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/billing_db",
        alias="BILLING_DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/2", alias="REDIS_URL")

    # Platform markup percentage (e.g. 0.055 = 5.5%)
    platform_markup: float = Field(default=0.055, alias="PLATFORM_MARKUP")


@lru_cache
def get_settings() -> BillingSettings:
    return BillingSettings()
