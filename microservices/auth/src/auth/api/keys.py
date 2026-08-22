"""Internal API key management endpoints.

Author: Farruh
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ai_routing_shared.models import ApiKeyTier
from ai_routing_shared.utils import generate_api_key, hash_api_key

from ..db.database import get_session
from ..db.models import ApiKeyRecord

router = APIRouter()


class CreateKeyRequest(BaseModel):
    name: str
    user_id: str = "system"
    tier: ApiKeyTier = ApiKeyTier.FREE
    monthly_budget_usd: Optional[float] = None
    allowed_models: Optional[List[str]] = None


class CreateKeyResponse(BaseModel):
    id: str
    key: str  # Raw key — only returned once
    name: str
    tier: str


@router.post("", response_model=CreateKeyResponse)
async def create_key(
    body: CreateKeyRequest,
    session: AsyncSession = Depends(get_session),
) -> CreateKeyResponse:
    """Create a new API key."""
    raw_key = generate_api_key(prefix="sk")
    key_id = f"key_{uuid.uuid4().hex[:16]}"

    record = ApiKeyRecord(
        id=key_id,
        name=body.name,
        key_hash=hash_api_key(raw_key),
        user_id=body.user_id,
        tier=body.tier.value,
        monthly_budget_usd=body.monthly_budget_usd,
        allowed_models=body.allowed_models,
    )
    session.add(record)
    await session.commit()

    return CreateKeyResponse(
        id=key_id,
        key=raw_key,
        name=body.name,
        tier=body.tier.value,
    )


@router.get("")
async def list_keys(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List all API keys (without raw key values)."""
    from sqlalchemy import select
    result = await session.execute(select(ApiKeyRecord))
    records = result.scalars().all()
    return {
        "keys": [
            {
                "id": r.id,
                "name": r.name,
                "user_id": r.user_id,
                "tier": r.tier,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }
