"""Safe asynchronous HTTP calls to isolated peer services.

The gateway is an HTTP boundary: peer responses are treated as untrusted data,
upstream bodies are never logged, and transport failures are mapped to domain
errors before they reach the public API.
"""

from __future__ import annotations

from typing import Any

import httpx
from ai_routing_shared.exceptions import UpstreamServiceError, UpstreamTimeoutError
from ai_routing_shared.utils import get_logger
from fastapi.responses import JSONResponse

logger = get_logger(__name__)


def _error_payload(response: httpx.Response) -> dict[str, Any]:
    """Return a stable public error envelope without echoing arbitrary bodies."""
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        return {"error": payload["error"]}

    if isinstance(payload, dict) and payload.get("detail"):
        detail = payload["detail"]
        message = detail if isinstance(detail, str) else "The upstream request was rejected."
        return {"error": {"code": "upstream_rejected", "message": message}}

    return {"error": {"code": "upstream_rejected", "message": "The upstream request was rejected."}}


def response_error_or_none(response: httpx.Response, service: str) -> JSONResponse | None:
    """Map an upstream HTTP response while preserving useful client 4xx errors.

    Peer 4xx responses are safe to expose through the common error envelope. A
    peer 5xx is not exposed verbatim because it may contain implementation
    details; it becomes a gateway-owned 502 error.
    """
    if response.status_code < 400:
        return None
    if response.status_code >= 500:
        raise UpstreamServiceError(
            f"{service.capitalize()} service returned an error.",
            service=service,
            details={"status": response.status_code},
        )
    return JSONResponse(_error_payload(response), status_code=response.status_code)


async def request_peer(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    service: str,
    **kwargs: Any,
) -> httpx.Response:
    """Execute an async peer request and map transport failures safely."""
    try:
        response = await client.request(method, path, **kwargs)
    except httpx.TimeoutException as exc:
        logger.warning("peer_timeout", peer_service=service, method=method, path=path)
        raise UpstreamTimeoutError(
            f"{service.capitalize()} service timed out.",
            service=service,
            details={"service": service},
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("peer_unreachable", peer_service=service, method=method, path=path)
        raise UpstreamServiceError(
            f"{service.capitalize()} service is temporarily unavailable.",
            service=service,
            details={"service": service},
        ) from exc
    return response


def response_json(response: httpx.Response, service: str) -> Any:
    """Parse a successful peer JSON response, never exposing parser details."""
    try:
        return response.json()
    except ValueError as exc:
        logger.error("peer_invalid_json", peer_service=service, status=response.status_code)
        raise UpstreamServiceError(
            f"{service.capitalize()} service returned an invalid response.",
            service=service,
            details={"status": response.status_code},
        ) from exc
