"""Internal key validation endpoint.

Called by the Gateway Service on every authenticated request.

Author: Farruh
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_routing_shared.exceptions import AuthenticationError
from ai_routing_shared.models import ApiKey, ApiKeyTier
from ai_routing_shared.utils import hash_api_key
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_session
from ..db.models import ApiKeyRecord

router = APIRouter()


class ValidateKeyRequest(BaseModel):
    raw_key: str


@router.post("/validate-key", response_model=ApiKey)
async def validate_key(
    body: ValidateKeyRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiKey:
    """Validate a raw API key and return the principal.

    Hashes the raw key and looks it up in the database. Returns the
    full ``ApiKey`` principal on success, or raises ``AuthenticationError``.
    """
    key_hash = hash_api_key(body.raw_key)

    result = await session.execute(
        select(ApiKeyRecord).where(
            ApiKeyRecord.key_hash == key_hash,
            ApiKeyRecord.is_active.is_(True),
        )
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise AuthenticationError("Invalid or expired API key.")

    record.last_used_at = datetime.now(UTC)
    await session.commit()

    return ApiKey(
        id=record.id,
        user_id=record.user_id,
        tier=ApiKeyTier(record.tier),
        requests_per_minute=record.requests_per_minute,
        requests_per_day=record.requests_per_day,
        monthly_budget_usd=record.monthly_budget_usd,
        allowed_models=record.allowed_models,
        is_active=record.is_active,
    )
