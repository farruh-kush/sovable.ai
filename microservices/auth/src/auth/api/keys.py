"""Role-guarded API-key management for portal administrators."""

from __future__ import annotations

import uuid

from ai_routing_shared.models import ApiKeyTier
from ai_routing_shared.utils import generate_api_key, hash_api_key
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_session
from ..db.models import ApiKeyRecord
from ..security.dependencies import InternalServicePrincipal, require_key_management_actor

router = APIRouter()


class CreateKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    user_id: str = "system"
    tier: ApiKeyTier = ApiKeyTier.FREE
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    allowed_models: list[str] | None = None
    requests_per_minute: int = Field(default=60, ge=1, le=100_000)
    requests_per_day: int = Field(default=2000, ge=1, le=10_000_000)


class CreateKeyResponse(BaseModel):
    id: str
    key: str  # Raw key — only returned once
    name: str
    tier: str


@router.post("", response_model=CreateKeyResponse)
async def create_key(
    body: CreateKeyRequest,
    session: AsyncSession = Depends(get_session),
    actor: UserAccount | InternalServicePrincipal = Depends(require_key_management_actor),
) -> CreateKeyResponse:
    """Create a key and return its raw value exactly once."""
    owner_id = actor.id if body.user_id == "system" else body.user_id
    if actor.role == "org_admin" and owner_id != actor.id:
        from ai_routing_shared.exceptions import AuthorisationError

        raise AuthorisationError("Organization administrators may only create keys for themselves.")
    raw_key = generate_api_key(prefix="sk")
    key_id = f"key_{uuid.uuid4().hex[:16]}"
    record = ApiKeyRecord(
        id=key_id,
        name=body.name,
        key_hash=hash_api_key(raw_key),
        user_id=owner_id,
        tier=body.tier.value,
        requests_per_minute=body.requests_per_minute,
        requests_per_day=body.requests_per_day,
        monthly_budget_usd=body.monthly_budget_usd,
        allowed_models=body.allowed_models,
    )
    session.add(record)
    await session.commit()
    return CreateKeyResponse(id=key_id, key=raw_key, name=body.name, tier=body.tier.value)


@router.get("")
async def list_keys(
    session: AsyncSession = Depends(get_session),
    actor: UserAccount | InternalServicePrincipal = Depends(require_key_management_actor),
) -> dict:
    """List metadata only; raw key values and hashes are never serialized."""
    query = select(ApiKeyRecord)
    if actor.role != "platform_controller":
        query = query.where(ApiKeyRecord.user_id == actor.id)
    records = (await session.execute(query)).scalars().all()
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


@router.delete("/{key_id}")
async def revoke_key(
    key_id: str,
    session: AsyncSession = Depends(get_session),
    actor: UserAccount | InternalServicePrincipal = Depends(require_key_management_actor),
) -> dict[str, str]:
    record = await session.get(ApiKeyRecord, key_id)
    if not record:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="API key not found")
    if actor.role != "platform_controller" and record.user_id != actor.id:
        from ai_routing_shared.exceptions import AuthorisationError

        raise AuthorisationError("You do not have permission to revoke this API key.")
    record.is_active = False
    await session.commit()
    return {"status": "revoked", "id": key_id}
