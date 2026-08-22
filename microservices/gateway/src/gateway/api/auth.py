"""Public auth proxy from Gateway to the private Auth Service.
Author: Farruh
"""
from __future__ import annotations
from typing import Any
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from ..core.config import GatewaySettings, get_settings

router = APIRouter()


def _forward_headers(request: Request) -> dict[str, str]:
    headers = {"content-type": request.headers.get("content-type", "application/json")}
    if request.headers.get("user-agent"):
        headers["user-agent"] = request.headers["user-agent"]
    return headers


async def _json_proxy(request: Request, path: str, body: dict[str, Any] | None = None) -> JSONResponse:
    settings: GatewaySettings = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.request(request.method, f"{settings.auth_service_url}{path}", json=body, headers=_forward_headers(request))
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": "Authentication service returned an invalid response"}
    return JSONResponse(payload, status_code=response.status_code)


@router.post("/auth/register/{channel}/start")
async def register_start(channel: str, request: Request) -> JSONResponse:
    return await _json_proxy(request, f"/auth/register/{channel}/start", await request.json())


@router.post("/auth/register/{channel}/verify")
async def register_verify(channel: str, request: Request) -> JSONResponse:
    return await _json_proxy(request, f"/auth/register/{channel}/verify", await request.json())


@router.post("/auth/refresh")
async def refresh(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/refresh", await request.json())


@router.post("/auth/logout")
async def logout(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/logout", await request.json())


@router.get("/auth/me")
async def me(request: Request) -> JSONResponse:
    return await _json_proxy(request, "/auth/me")


@router.get("/auth/oauth/{provider}/start")
async def oauth_start(provider: str, request: Request) -> Any:
    settings: GatewaySettings = get_settings()
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.get(f"{settings.auth_service_url}/auth/oauth/{provider}/start")
    if response.is_redirect and response.headers.get("location"):
        return RedirectResponse(response.headers["location"], status_code=response.status_code)
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": "Authentication provider unavailable"}
    return JSONResponse(payload, status_code=response.status_code)


@router.get("/auth/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request) -> Any:
    settings: GatewaySettings = get_settings()
    query = str(request.url.query)
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.get(f"{settings.auth_service_url}/auth/oauth/{provider}/callback?{query}")
    if response.is_redirect and response.headers.get("location"):
        return RedirectResponse(response.headers["location"], status_code=response.status_code)
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": "Authentication callback failed"}
    return JSONResponse(payload, status_code=response.status_code)
