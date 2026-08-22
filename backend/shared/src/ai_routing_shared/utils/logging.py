"""Structured JSON logging configuration using structlog.

All microservices call ``configure_logging()`` at startup to ensure
consistent, machine-parseable log output compatible with ELK / OpenTelemetry.

Author: Farruh
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(level: str = "INFO", service_name: str = "ai-routing") -> None:
    """Configure structlog for JSON output.

    Args:
        level: Python logging level string (e.g. ``"INFO"``, ``"DEBUG"``).
        service_name: Injected into every log record as ``service``.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Bind the service name to every log record
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str) -> Any:
    """Return a structlog logger bound to the given name."""
    return structlog.get_logger(name)
