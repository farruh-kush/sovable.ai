"""Activity Logs API — /internal/generations.

Phase 3 — Task 3.3: Provides per-request generation detail including
exact token breakdown, cost, latency, and cache status.

Author: Farruh
"""

from __future__ import annotations

from ai_routing_shared.models import GenerationCost, GenerationRecord, UsageInfo
from ai_routing_shared.utils import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_session
from ..db.models import UsageRecordORM

router = APIRouter()
logger = get_logger(__name__)


@router.get("/generations/{generation_id}", response_model=GenerationRecord)
async def get_generation(
    generation_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> GenerationRecord:
    """Return detailed metadata for a specific generation.

    The ``user_id`` parameter is provided by the Gateway after authenticating
    the request, ensuring users can only access their own records.
    """
    result = await session.execute(select(UsageRecordORM).where(UsageRecordORM.id == generation_id))
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Generation not found.")

    # Enforce ownership — users can only see their own generations
    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    usage = UsageInfo(
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        total_tokens=record.total_tokens,
        estimated_cost_usd=record.cost_usd,
        cached_tokens=record.cached_tokens,
        cache_discount_usd=record.cache_discount_usd,
        cache_hit=record.cache_hit,
    )

    cost = GenerationCost(
        prompt_cost_usd=round(record.cost_usd - record.markup_usd, 8),
        completion_cost_usd=0.0,  # Broken out in the pricing catalog
        cache_discount_usd=record.cache_discount_usd,
        total_cost_usd=record.cost_usd,
        markup_usd=record.markup_usd,
        billed_usd=record.billed_usd,
    )

    return GenerationRecord(
        id=record.id,
        model=record.model,
        provider=record.provider,
        created_at=record.created_at,
        usage=usage,
        cost=cost,
        latency_ms=record.latency_ms,
        fallback_used=record.fallback_used,
        cache_hit=record.cache_hit,
    )


@router.get("/usage/monthly/{api_key_id}")
async def get_monthly_spend(
    api_key_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the current month's total spend for an API key."""
    from datetime import datetime

    from sqlalchemy import extract, func

    now = datetime.utcnow()
    result = await session.execute(
        select(func.sum(UsageRecordORM.billed_usd)).where(
            UsageRecordORM.api_key_id == api_key_id,
            extract("year", UsageRecordORM.created_at) == now.year,
            extract("month", UsageRecordORM.created_at) == now.month,
        )
    )
    total = result.scalar_one_or_none() or 0.0
    return {"api_key_id": api_key_id, "monthly_spend_usd": round(total, 6)}
