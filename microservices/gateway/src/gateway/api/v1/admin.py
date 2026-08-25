"""Protected administrative overview endpoints.

The gateway is the only public entry point. This endpoint aggregates safe,
non-secret operational signals from internal services for the Admin Console.
Author: Farruh
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException

from ...core.config import GatewaySettings, get_settings

router = APIRouter()


def require_admin_key(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    settings: GatewaySettings = Depends(get_settings),
) -> None:
    """Require the configured management key without exposing comparison details."""
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status_code=403, detail="Admin access required")


async def _safe_get(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    """Read an internal JSON endpoint and return a sanitized unavailable result on failure."""
    try:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"status": "invalid_response"}
    except (httpx.HTTPError, ValueError):
        return {"status": "unavailable"}


@router.get("/admin/overview", dependencies=[Depends(require_admin_key)])
async def admin_overview(
    settings: GatewaySettings = Depends(get_settings),
) -> dict[str, Any]:
    """Return a safe operational snapshot for the Admin Console."""
    async with httpx.AsyncClient(timeout=8.0) as client:
        router_health = await _safe_get(client, f"{settings.router_service_url}/health")
        models = await _safe_get(client, f"{settings.router_service_url}/route/models")
        routing = await _safe_get(client, f"{settings.router_service_url}/route/routing/summary")
        provider_health = await _safe_get(client, f"{settings.provider_service_url}/health")

    providers = provider_health.get("providers", {})
    provider_items = [
        {
            "name": name,
            "configured": bool(details.get("configured", False)),
            "circuit_open": bool(details.get("circuit_open", False)),
            "error_count": int(details.get("error_count", 0) or 0),
            "last_latency_ms": details.get("last_latency_ms"),
        }
        for name, details in sorted(providers.items())
        if isinstance(details, dict)
    ]
    model_items = models.get("data", []) if isinstance(models.get("data"), list) else []
    configured_count = sum(1 for item in provider_items if item["configured"])
    circuit_count = sum(1 for item in provider_items if item["circuit_open"])

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "gateway": {"status": "healthy", "service": "gateway"},
        "router": router_health,
        "provider": {
            "status": provider_health.get("status", "unavailable"),
            "service": provider_health.get("service", "provider"),
        },
        "providers": provider_items,
        "models": {"object": "list", "data": model_items},
        "routing": routing,
        "summary": {
            "providers_total": len(provider_items),
            "providers_configured": configured_count,
            "circuits_open": circuit_count,
            "models_total": len(model_items),
        },
    }
