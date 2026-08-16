"""Auth Service configuration.

Author: Farruh
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/auth_db",
        alias="DATABASE_URL",
    )
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")


@lru_cache
def get_settings() -> AuthSettings:
    return AuthSettings()
