"""Public authentication proxy from Gateway to the private Auth Service."""

from __future__ import annotations

from typing import Any

import httpx
from ai_routing_shared.exceptions import SchemaValidationError
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..core.config import GatewaySettings, get_settings
from ..core.downstream import request_peer, response_error_or_none, response_json

router = APIRouter()


async def _json_body(request: Request) -> dict[str, Any]:
    """Read a JSON object body without echoing malformed input."""
    try:
        payload = await request.json()
    except ValueError as exc:
        raise SchemaValidationError(
            "Request body must be valid JSON.",
            details={"field": "body"},
        ) from exc
    if not isinstance(payload, dict):
        raise SchemaValidationError(
            "Request body must be a JSON object.",
            details={"field": "body"},
        )
    return payload


def _forward_headers(request: Request) -> dict[str, str]:
    """Forward only headers required for Auth semantics and traceability."""
    headers: dict[str, str] = {}
    for name in ("content-type", "user-agent", "authorization", "cookie"):
        value = request.headers.get(name)
        if value:
            headers[name] = value
    request_id = request.headers.get("x-request-id")
    if request_id:
        headers["x-request-id"] = request_id
    return headers


async def _json_proxy(
    request: Request, path: str, body: dict[str, Any] | None = None
) -> JSONResponse:
    settings: GatewaySettings = get_settings()
    async with httpx.AsyncClient(base_url=settings.auth_service_url, timeout=15.0) as client:
        response = await request_peer(
            client,
            request.method,
            path,
            service="auth",
            json=body,
            headers=_forward_headers(request),
        )
    mapped = response_error_or_none(response, "auth")
    if mapped is not None:
        return mapped
    return JSONResponse(response_json(response, "auth"), status_code=response.status_code)


@router.post("/auth/register/{channel}/start")
async def register_start(channel: str, request: Request) -> JSONResponse:
    return await _json_proxy(request, f"/auth/register/{channel}/start", await _json_body(request))


@router.post("/auth/register/{channel}/verify")
async def register_verify(channel: str, request: Request) -> JSONResponse:
    return await _json_proxy(request, f"/auth/register/{channel}/verify", await _json_body(request))


@router.post("/auth/email/activation/start")
async def activation_start(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/email/activation/start", await _json_body(request))


@router.post("/auth/email/activation/complete")
async def activation_complete(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/email/activation/complete", await _json_body(request))


@router.post("/auth/login")
async def login(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/login", await _json_body(request))


@router.post("/auth/link")
async def link(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/link", await _json_body(request))


@router.delete("/auth/link/{provider}")
async def unlink(provider: str, request: Request) -> JSONResponse:
    return await _json_proxy(request, f"/auth/link/{provider}")


@router.patch("/auth/users/{user_id}/role")
async def update_role(user_id: str, request: Request) -> JSONResponse:
    return await _json_proxy(request, f"/auth/users/{user_id}/role", await _json_body(request))


@router.post("/auth/refresh")
async def refresh(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/refresh", await _json_body(request))


@router.post("/auth/logout")
async def logout(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/logout", await _json_body(request))


@router.get("/auth/me")
async def me(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/me")


@router.post("/v1/keys")
async def create_key(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/v1/keys", await _json_body(request))


@router.get("/v1/keys")
async def list_keys(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/v1/keys")


@router.delete("/v1/keys/{key_id}")
async def revoke_key(key_id: str, request: Request) -> JSONResponse:
    return await _json_proxy(request, f"/v1/keys/{key_id}")


async def _oauth_proxy(request: Request, path: str) -> Any:
    settings: GatewaySettings = get_settings()
    async with httpx.AsyncClient(
        base_url=settings.auth_service_url, timeout=15.0, follow_redirects=False
    ) as client:
        response = await request_peer(
            client,
            "GET",
            path,
            service="auth",
            headers=_forward_headers(request),
        )
    if response.is_redirect and response.headers.get("location"):
        return RedirectResponse(response.headers["location"], status_code=response.status_code)
    mapped = response_error_or_none(response, "auth")
    if mapped is not None:
        return mapped
    return JSONResponse(response_json(response, "auth"), status_code=response.status_code)


@router.get("/auth/oauth/{provider}/start")
async def oauth_start(provider: str, request: Request) -> Any:
    return await _oauth_proxy(request, f"/auth/oauth/{provider}/start")


@router.get("/auth/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request) -> Any:
    query = str(request.url.query)
    path = f"/auth/oauth/{provider}/callback"
    if query:
        path = f"{path}?{query}"
    return await _oauth_proxy(request, path)
