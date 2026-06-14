from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="AI Routing Layer", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db",
        alias="DATABASE_URL",
    )
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    default_timeout_seconds: float = Field(default=30.0, alias="DEFAULT_TIMEOUT_SECONDS")
    routing_config_path: Path = Field(
        default=Path("./config/routing.yaml"),
        alias="ROUTING_CONFIG_PATH",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
