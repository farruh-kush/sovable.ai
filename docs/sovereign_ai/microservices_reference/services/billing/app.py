from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import FastAPI, Header, HTTPException

from shared.config import settings
from shared.models import HealthResponse, QuotaCheckRequest, QuotaCheckResponse, UsageEvent, UsageReceipt


config = settings("billing", 8104)
app = FastAPI(title="AI Routing Billing Service", version="0.1.0")
LOCK = asyncio.Lock()
TOTALS: defaultdict[str, float] = defaultdict(float)
REQUESTS: dict[str, UsageEvent] = {}


def require_internal(secret: str | None) -> None:
    if secret != config.internal_secret:
        raise HTTPException(status_code=401, detail="invalid internal service credential")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=config.service_name, status="ok")


@app.post("/internal/quota/check", response_model=QuotaCheckResponse)
async def quota_check(payload: QuotaCheckRequest, x_internal_secret: str | None = Header(default=None)) -> QuotaCheckResponse:
    require_internal(x_internal_secret)
    async with LOCK:
        current = TOTALS[payload.principal.organization_id]
    projected = current + payload.estimated_cost_usd
    allowed = projected <= config.monthly_budget_usd or payload.principal.tier == "admin"
    reason = None if allowed else "monthly organization budget would be exceeded"
    return QuotaCheckResponse(
        allowed=allowed,
        monthly_cost_usd=round(current, 6),
        monthly_budget_usd=config.monthly_budget_usd,
        reason=reason,
    )


@app.post("/internal/usage", response_model=UsageReceipt)
async def record_usage(payload: UsageEvent, x_internal_secret: str | None = Header(default=None)) -> UsageReceipt:
    require_internal(x_internal_secret)
    async with LOCK:
        if payload.request_id not in REQUESTS:
            REQUESTS[payload.request_id] = payload
            TOTALS[payload.principal.organization_id] += payload.estimated_cost_usd
        monthly = TOTALS[payload.principal.organization_id]
    alert = "budget-warning" if monthly >= config.monthly_budget_usd * 0.8 else None
    return UsageReceipt(
        request_id=payload.request_id,
        recorded=True,
        total_cost_usd=round(payload.estimated_cost_usd, 6),
        monthly_cost_usd=round(monthly, 6),
        alert=alert,
    )
