from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from shared.config import settings
from shared.models import HealthResponse, RouteDecision, RouteRequest


config = settings("router", 8102)
app = FastAPI(title="AI Routing Router Service", version="0.1.0")
POLICY_PATH = Path(os.getenv("ROUTING_CONFIG_PATH", str(Path(__file__).resolve().parents[2] / "config" / "routing.json")))
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def require_internal(secret: str | None) -> None:
    if secret != config.internal_secret:
        raise HTTPException(status_code=401, detail="invalid internal service credential")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=config.service_name, status="ok")


@app.post("/internal/route", response_model=RouteDecision)
async def route(payload: RouteRequest, x_internal_secret: str | None = Header(default=None)) -> RouteDecision:
    require_internal(x_internal_secret)
    model_policy = POLICY["models"].get(payload.requested_model)
    if model_policy is None:
        raise HTTPException(status_code=400, detail=f"model is not allowed: {payload.requested_model}")
    if model_policy["external"] and not payload.allow_external:
        raise HTTPException(status_code=403, detail="external routing is disabled for this request")
    if payload.principal.tier == "free" and model_policy["external"]:
        raise HTTPException(status_code=403, detail="free tier cannot use external models")
    fallbacks = POLICY.get("fallbacks", {}).get(payload.requested_model, [])
    return RouteDecision(
        provider=model_policy["provider"],
        provider_model=model_policy["provider_model"],
        endpoint=model_policy["endpoint"],
        fallback_chain=fallbacks,
        reason=("external allowlisted model" if model_policy["external"] else "local residency policy"),
        unit_cost_usd_per_1k=model_policy["cost_per_1k_tokens"],
        estimated_cost_usd=round(payload.estimated_tokens / 1000 * model_policy["cost_per_1k_tokens"], 6),
    )
