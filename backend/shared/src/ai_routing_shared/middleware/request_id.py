"""Request ID middleware.

Injects a unique ``X-Request-Id`` header into every request and response,
enabling distributed tracing across microservices.

Author: Farruh
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every inbound request."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        structlog.contextvars.unbind_contextvars("request_id")
        return response


from typing import Any
