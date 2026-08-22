"""Unified error handler for all FastAPI microservices.

Maps the shared exception hierarchy to consistent JSON error responses,
ensuring that every service returns the same error envelope format.

Author: Farruh
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from ai_routing_shared.exceptions import RoutingLayerError
from ai_routing_shared.utils import get_logger

logger = get_logger(__name__)


async def error_handler_middleware(request: Request, call_next: Any) -> Any:
    """Catch ``RoutingLayerError`` and return a structured JSON error response."""
    try:
        return await call_next(request)
    except RoutingLayerError as exc:
        logger.warning(
            "routing_layer_error",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            status=exc.http_status,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    **exc.details,
                }
            },
        )
    except Exception as exc:
        logger.exception("unhandled_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An unexpected error occurred."}},
        )


from typing import Any  # noqa: E402
