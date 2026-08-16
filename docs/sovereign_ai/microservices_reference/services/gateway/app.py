from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from shared.config import settings
from shared.http import ServiceCallError, post_json
from shared.models import ChatRequest, HealthResponse
from shared.privacy import PrivacyEngine


config = settings("gateway", 8100)
app = FastAPI(title="AI Routing Gateway", version="0.1.0")
privacy = PrivacyEngine()


def internal_payload(headers: dict[str, str]) -> dict[str, str]:
    return {"X-Internal-Secret": config.internal_secret, **headers}


async def call_service(base_url: str, path: str, payload: dict[str, Any], service: str) -> dict[str, Any]:
    return await post_json(base_url, path, payload, config.internal_secret, service)


async def service_health(base_url: str, service: str) -> dict[str, Any]:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{base_url.rstrip('/')}/health")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise ServiceCallError(service, 503, str(exc)) from exc


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=config.service_name, status="ok")


@app.get("/ready")
async def ready() -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, url in (("auth", config.auth_url), ("router", config.router_url), ("provider", config.provider_url), ("billing", config.billing_url)):
        try:
            checks[name] = await service_health(url, name)
        except ServiceCallError as exc:
            checks[name] = {"status": "down", "detail": str(exc)}
    ready_state = all(item.get("status") == "ok" for item in checks.values())
    return {"ready": ready_state, "checks": checks}


@app.get("/v1/models")
async def models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {"id": "local", "object": "model", "owned_by": "sovereign-platform"},
            {"id": "gpt-4o-mini", "object": "model", "owned_by": "approved-provider"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatRequest,
    http_request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if request.stream:
        raise HTTPException(status_code=400, detail="streaming is deferred in this reference implementation")
    api_key = (authorization or "").removeprefix("Bearer ").strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="Bearer API key is required")
    request_id = http_request.headers.get("X-Request-ID", uuid.uuid4().hex)
    started = time.perf_counter()

    try:
        authorized = await call_service(
            config.auth_url,
            "/internal/authorize",
            {"api_key": api_key, "required_scope": "chat:complete"},
            "auth",
        )
        principal = authorized["principal"]
        masked_messages, mapping, entities = privacy.mask_messages([message.model_dump() for message in request.messages])
        masked_request = ChatRequest.model_validate({**request.model_dump(exclude_none=True), "messages": masked_messages})
        estimated_tokens = max(1, sum(len(str(message.get("content", "")).split()) for message in masked_messages))
        allow_external = request.metadata.get("allow_external", False) is True and principal["tier"] != "free"
        route = await call_service(
            config.router_url,
            "/internal/route",
            {
                "request_id": request_id,
                "requested_model": request.model,
                "principal": principal,
                "allow_external": allow_external,
                "estimated_tokens": estimated_tokens,
            },
            "router",
        )
        quota = await call_service(
            config.billing_url,
            "/internal/quota/check",
            {"principal": principal, "estimated_cost_usd": route["estimated_cost_usd"]},
            "billing",
        )
        if not quota["allowed"]:
            raise HTTPException(status_code=429, detail=quota["reason"])
        provider_result = await call_service(
            config.provider_url,
            "/internal/chat",
            {
                "request_id": request_id,
                "route": route,
                "chat": masked_request.model_dump(exclude_none=True),
            },
            "provider",
        )
        restored = privacy.restore_payload(provider_result["response"], mapping)
        elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))
        usage = await call_service(
            config.billing_url,
            "/internal/usage",
            {
                "request_id": request_id,
                "principal": principal,
                "provider": provider_result["provider"],
                "model": provider_result["model"],
                "input_tokens": provider_result["input_tokens"],
                "output_tokens": provider_result["output_tokens"],
                "latency_ms": elapsed_ms,
                "estimated_cost_usd": provider_result["estimated_cost_usd"],
            },
            "billing",
        )
    except HTTPException:
        raise
    except ServiceCallError as exc:
        status = 502 if exc.status_code in {502, 503} else exc.status_code
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    if not isinstance(restored, dict):
        raise HTTPException(status_code=502, detail="provider returned a non-object response")
    restored["x_routing"] = {
        "request_id": request_id,
        "provider": provider_result["provider"],
        "model": provider_result["model"],
        "route_reason": route["reason"],
        "fallback_chain": route["fallback_chain"],
        "masked_entity_count": len(entities),
        "entity_types": sorted({entity.entity_type for entity in entities}),
        "latency_ms": elapsed_ms,
        "usage_recorded": usage["recorded"],
    }
    return restored
