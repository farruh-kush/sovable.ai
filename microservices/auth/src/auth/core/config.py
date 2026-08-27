"""Configuration for the Auth and Identity Service.

Sensitive values use ``SecretStr`` so accidental repr/logging redacts them. In
Kubernetes, populate these fields from ``Secret`` keys rather than committing
values to manifests or images.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/auth_db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    secret_key: SecretStr = Field(default=SecretStr("change-me-in-production"), alias="SECRET_KEY")
    internal_service_key: SecretStr = Field(
        default=SecretStr(""), alias="AUTH_INTERNAL_SERVICE_KEY"
    )
    public_base_url: str = Field(default="https://api.sovable.ai", alias="PUBLIC_BASE_URL")
    frontend_base_url: str = Field(default="https://sovable.ai", alias="FRONTEND_BASE_URL")
    access_token_ttl_seconds: int = Field(default=900, alias="ACCESS_TOKEN_TTL_SECONDS", ge=60)
    refresh_token_ttl_days: int = Field(default=30, alias="REFRESH_TOKEN_TTL_DAYS", ge=1)
    otp_ttl_seconds: int = Field(default=600, alias="OTP_TTL_SECONDS", ge=60)
    otp_max_attempts: int = Field(default=5, alias="OTP_MAX_ATTEMPTS", ge=1, le=20)
    otp_delivery_mode: str = Field(default="disabled", alias="OTP_DELIVERY_MODE")
    allow_dev_otp: bool = Field(default=False, alias="ALLOW_DEV_OTP")
    activation_link_ttl_seconds: int = Field(
        default=3600, alias="ACTIVATION_LINK_TTL_SECONDS", ge=60
    )
    activation_email_provider: str = Field(default="directmail", alias="ACTIVATION_EMAIL_PROVIDER")
    directmail_access_key_id: SecretStr = Field(
        default=SecretStr(""), alias="DIRECTMAIL_ACCESS_KEY_ID"
    )
    directmail_access_key_secret: SecretStr = Field(
        default=SecretStr(""), alias="DIRECTMAIL_ACCESS_KEY_SECRET"
    )
    directmail_endpoint: str = Field(
        default="dm.ap-southeast-1.aliyuncs.com", alias="DIRECTMAIL_ENDPOINT"
    )
    directmail_account_name: str = Field(default="", alias="DIRECTMAIL_ACCOUNT_NAME")
    directmail_from_alias: str = Field(default="Solvable AI", alias="DIRECTMAIL_FROM_ALIAS")
    directmail_timeout_seconds: int = Field(
        default=30, alias="DIRECTMAIL_TIMEOUT_SECONDS", ge=1, le=120
    )
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: SecretStr = Field(default=SecretStr(""), alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="", alias="GOOGLE_REDIRECT_URI")
    apple_client_id: str = Field(default="", alias="APPLE_CLIENT_ID")
    apple_team_id: str = Field(default="", alias="APPLE_TEAM_ID")
    apple_key_id: str = Field(default="", alias="APPLE_KEY_ID")
    apple_private_key: SecretStr = Field(default=SecretStr(""), alias="APPLE_PRIVATE_KEY")
    apple_redirect_uri: str = Field(default="", alias="APPLE_REDIRECT_URI")
    oidc_providers_json: str = Field(default="{}", alias="OIDC_PROVIDERS_JSON")
    login_rate_limit: int = Field(default=10, alias="LOGIN_RATE_LIMIT", ge=1)
    activation_rate_limit: int = Field(default=5, alias="ACTIVATION_RATE_LIMIT", ge=1)
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS", ge=1)
    rate_limit_backend: str = Field(default="memory", alias="RATE_LIMIT_BACKEND")


@lru_cache
def get_settings() -> AuthSettings:
    return AuthSettings()
