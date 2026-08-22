"""Authentication and policy enforcement dependencies for the Gateway.

This module implements the three critical bug fixes from Phase 1:
  - Task 1.1: Rate limiting (delegated to RedisClient)
  - Task 1.2: Monthly budget cap enforcement
  - Task 1.3: Model whitelist enforcement

Author: Farruh
"""

from __future__ import annotations

from typing import Optional

import httpx
from fastapi import Depends, Header, Request

from ai_routing_shared.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    ModelNotAllowedError,
    RateLimitError,
)
from ai_routing_shared.models import ApiKey
from ai_routing_shared.utils import get_logger

from .config import GatewaySettings, get_settings

logger = get_logger(__name__)


async def get_api_key(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    settings: GatewaySettings = Depends(get_settings),
) -> ApiKey:
    """Validate the API key by calling the Auth Service.

    Extracts the raw key from either the ``Authorization: Bearer <key>``
    header or the ``X-Api-Key`` header, then delegates validation to the
    Auth Service, which returns the full ``ApiKey`` principal.

    Args:
        request: The incoming FastAPI request (used to access app state).
        authorization: Value of the ``Authorization`` header.
        x_api_key: Value of the ``X-Api-Key`` header.
        settings: Injected gateway settings.

    Returns:
        A validated ``ApiKey`` principal.

    Raises:
        AuthenticationError: If the key is missing or invalid.
    """
    raw_key = x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        raw_key = authorization[7:]

    if not raw_key:
        raise AuthenticationError("Missing API key. Provide it via 'Authorization: Bearer <key>'.")

    async with httpx.AsyncClient(base_url=settings.auth_service_url, timeout=5.0) as client:
        try:
            response = await client.post(
                "/internal/validate-key",
                json={"raw_key": raw_key},
            )
        except httpx.RequestError as exc:
            logger.error("auth_service_unreachable", error=str(exc))
            raise AuthenticationError("Authentication service is temporarily unavailable.")

    if response.status_code == 401:
        raise AuthenticationError("Invalid or expired API key.")

    if response.status_code != 200:
        logger.error("auth_service_error", status=response.status_code, body=response.text)
        raise AuthenticationError("Authentication service returned an unexpected error.")

    return ApiKey.model_validate(response.json())


async def enforce_rate_limit(
    request: Request,
    api_key: ApiKey = Depends(get_api_key),
) -> ApiKey:
    """Phase 1 — Task 1.1: Enforce per-minute and per-day rate limits.

    Uses the Redis sliding window implementation in ``RedisClient``.
    """
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
    """Phase 1 — Task 1.2: Enforce the monthly budget cap.

    Checks the current month's spend from Redis (written by the Billing
    Service) before routing the request. Blocks with HTTP 429 if the
    budget has been reached.
    """
    if api_key.monthly_budget_usd is None:
        return api_key  # No budget configured — allow all requests

    redis = request.app.state.redis
    current_spend = await redis.get_monthly_spend(api_key.id)

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
    """Phase 1 — Task 1.3: Enforce the model whitelist.

    Args:
        model: The model requested by the client.
        api_key: The validated API key principal.

    Raises:
        ModelNotAllowedError: If the model is not in the key's whitelist.
    """
    if api_key.allowed_models and model not in api_key.allowed_models:
        raise ModelNotAllowedError(
            f"Model '{model}' is not permitted for this API key.",
            details={"allowed_models": api_key.allowed_models},
        )
