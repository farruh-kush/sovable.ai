"""Gateway authentication and request policy dependencies."""

from __future__ import annotations

import hmac

import httpx
from ai_routing_shared.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    ModelNotAllowedError,
    RateLimitError,
    UpstreamServiceError,
    UpstreamTimeoutError,
)
from ai_routing_shared.models import ApiKey
from ai_routing_shared.utils import get_logger
from fastapi import Depends, Header, Request
from pydantic import ValidationError

from .config import GatewaySettings, get_settings

logger = get_logger(__name__)


def _extract_raw_key(authorization: str | None, x_api_key: str | None) -> str:
    """Extract one API key and reject ambiguous authentication headers."""
    bearer_key: str | None = None
    if authorization is not None:
        scheme, separator, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and separator:
            bearer_key = value.strip()
        elif authorization.strip():
            raise AuthenticationError("Invalid Authorization header. Use 'Bearer <key>'.")

    header_key = x_api_key.strip() if x_api_key else None
    if bearer_key and header_key and not hmac.compare_digest(bearer_key, header_key):
        raise AuthenticationError("Conflicting API-key headers were provided.")

    raw_key = bearer_key or header_key
    if not raw_key:
        raise AuthenticationError("Missing API key. Provide it via 'Authorization: Bearer <key>'.")
    return raw_key


async def get_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    settings: GatewaySettings = Depends(get_settings),
) -> ApiKey:
    """Validate a client API key through the private Auth Service."""
    raw_key = _extract_raw_key(authorization, x_api_key)
    headers: dict[str, str] = {}
    request_id = request.headers.get("x-request-id")
    if request_id:
        headers["x-request-id"] = request_id

    async with httpx.AsyncClient(base_url=settings.auth_service_url, timeout=5.0) as client:
        try:
            response = await client.post(
                "/internal/validate-key",
                json={"raw_key": raw_key},
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            logger.warning("auth_service_timeout")
            raise UpstreamTimeoutError(
                "Authentication service timed out.",
                service="auth",
                details={"service": "auth"},
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("auth_service_unreachable")
            raise UpstreamServiceError(
                "Authentication service is temporarily unavailable.",
                service="auth",
                details={"service": "auth"},
            ) from exc

    if response.status_code in {401, 403}:
        raise AuthenticationError("Invalid or expired API key.")
    if response.status_code >= 500:
        logger.error("auth_service_error", status=response.status_code)
        raise UpstreamServiceError(
            "Authentication service returned an error.",
            service="auth",
            details={"status": response.status_code, "service": "auth"},
        )
    if response.status_code != 200:
        raise AuthenticationError("Authentication service rejected the API key.")

    try:
        payload = response.json()
        return ApiKey.model_validate(payload)
    except (ValueError, ValidationError) as exc:
        logger.error("auth_service_invalid_response", status=response.status_code)
        raise UpstreamServiceError(
            "Authentication service returned an invalid response.",
            service="auth",
            details={"service": "auth"},
        ) from exc


async def enforce_rate_limit(
    request: Request,
    api_key: ApiKey = Depends(get_api_key),
) -> ApiKey:
    """Enforce per-minute and per-day sliding-window limits."""
    redis = request.app.state.redis
    minute_key = f"rl:{api_key.id}:minute"
    day_key = f"rl:{api_key.id}:day"

    minute_ok = await redis.check_rate_limit(minute_key, api_key.requests_per_minute, 60)
    if not minute_ok:
        raise RateLimitError(
            "Per-minute rate limit exceeded.",
            details={"limit": api_key.requests_per_minute, "window": "1m"},
        )

    day_ok = await redis.check_rate_limit(day_key, api_key.requests_per_day, 86400)
    if not day_ok:
        raise RateLimitError(
            "Per-day rate limit exceeded.",
            details={"limit": api_key.requests_per_day, "window": "24h"},
        )

    return api_key


async def enforce_budget(
    request: Request,
    api_key: ApiKey = Depends(enforce_rate_limit),
) -> ApiKey:
    """Enforce the configured monthly spend cap before routing."""
    if api_key.monthly_budget_usd is None:
        return api_key

    current_spend = await request.app.state.redis.get_monthly_spend(api_key.id)
    if current_spend >= api_key.monthly_budget_usd:
        raise BudgetExceededError(
            f"Monthly budget of ${api_key.monthly_budget_usd:.2f} USD has been reached.",
            details={
                "spend": round(current_spend, 6),
                "budget": api_key.monthly_budget_usd,
            },
        )
    return api_key


def enforce_model_whitelist(model: str, api_key: ApiKey) -> None:
    """Reject models not permitted by the validated API-key principal."""
    if api_key.allowed_models and model not in api_key.allowed_models:
        raise ModelNotAllowedError(
            f"Model '{model}' is not permitted for this API key.",
            details={"allowed_models": api_key.allowed_models},
        )
