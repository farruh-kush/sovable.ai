from __future__ import annotations

from typing import Any

import httpx


class ServiceCallError(RuntimeError):
    def __init__(self, service: str, status_code: int, detail: Any) -> None:
        super().__init__(f"{service} returned HTTP {status_code}: {detail}")
        self.service = service
        self.status_code = status_code
        self.detail = detail


async def post_json(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    internal_secret: str,
    service: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/{path.lstrip('/')}",
                headers={"X-Internal-Secret": internal_secret, "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise ServiceCallError(service, 503, str(exc)) from exc
    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text}
    if response.status_code >= 400:
        raise ServiceCallError(service, response.status_code, body)
    if not isinstance(body, dict):
        raise ServiceCallError(service, 502, body)
    return body
