"""Usage event ingestion endpoint.

Receives asynchronous usage events from the Router Engine Service,
calculates the full cost breakdown, persists the record, and updates
the monthly spend counter in Redis for fast budget enforcement.

Author: Farruh
"""

from __future__ import annotations

from ai_routing_shared.models import UsageRecord
from ai_routing_shared.utils import get_logger
from fastapi import APIRouter, Depends
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import BillingSettings, get_settings
from ..db.database import get_session
from ..db.models import UsageRecordORM
from ..pricing.catalog import PricingCatalog

router = APIRouter()
logger = get_logger(__name__)


@router.post("/usage", status_code=202)
async def ingest_usage(
    record: UsageRecord,
    session: AsyncSession = Depends(get_session),
    settings: BillingSettings = Depends(get_settings),
) -> dict:
    """Ingest a usage event from the Router Engine.

    Calculates the full cost breakdown, applies the platform markup,
    and persists the enriched record. Also updates the monthly spend
    counter in Redis so the Gateway can enforce budget caps in real time.
    """
    catalog = PricingCatalog(markup=settings.platform_markup)
    costs = catalog.calculate(
        provider=record.provider,
        model=record.model,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        cached_tokens=record.cached_tokens,
    )

    orm_record = UsageRecordORM(
        id=record.id,
        api_key_id=record.api_key_id,
        user_id=record.user_id,
        model=record.model,
        provider=record.provider,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        total_tokens=record.total_tokens,
        cost_usd=costs["total_cost_usd"],
        markup_usd=costs["markup_usd"],
        billed_usd=costs["billed_usd"],
        latency_ms=record.latency_ms,
        fallback_used=record.fallback_used,
        cache_hit=record.cache_hit,
        cached_tokens=record.cached_tokens,
        cache_discount_usd=costs["cache_discount_usd"],
        experiment_name=record.experiment_name,
        experiment_variant=record.experiment_variant,
        schema_validation_passed=record.schema_validation_passed,
        validation_retry_count=record.validation_retry_count,
    )

    session.add(orm_record)
    await session.commit()

    # Update the monthly spend counter in Redis for fast budget enforcement
    # The Gateway reads this value to enforce monthly_budget_usd
    await _update_monthly_spend(
        api_key_id=record.api_key_id,
        amount=costs["billed_usd"],
        redis_url=settings.redis_url,
    )

    logger.info(
        "usage_ingested",
        generation_id=record.id,
        provider=record.provider,
        model=record.model,
        billed_usd=costs["billed_usd"],
        cache_hit=record.cache_hit,
    )

    return {"status": "accepted", "generation_id": record.id}


async def _update_monthly_spend(api_key_id: str, amount: float, redis_url: str) -> None:
    """Increment the monthly spend counter in Redis."""
    try:
        from datetime import datetime

        import redis.asyncio as aioredis

        client = aioredis.from_url(redis_url, decode_responses=True)
        key = f"spend:{api_key_id}:monthly"
        # Use INCRBYFLOAT for atomic float increment
        await client.incrbyfloat(key, amount)
        # Set TTL to end of current month + 1 day buffer
        now = datetime.utcnow()
        days_in_month = 32 - datetime(now.year, now.month, 32).day if now.month < 12 else 31
        ttl = (days_in_month - now.day + 2) * 86400
        await client.expire(key, ttl)
        await client.aclose()
    except (RedisError, OSError, TimeoutError, ValueError) as exc:
        logger.error("redis_spend_update_failed", error=str(exc), api_key_id=api_key_id)
