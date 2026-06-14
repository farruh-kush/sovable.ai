"""Unified exception hierarchy for the AI Routing Layer.

All microservices raise exceptions from this hierarchy, which are then
mapped to consistent HTTP error responses by the API Gateway.

Author: Farruh
"""

from __future__ import annotations

from typing import Optional


class RoutingLayerError(Exception):
    """Base exception for all AI Routing Layer errors."""

    http_status: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ── Authentication & Authorisation ──────────────────────────────────────────

class AuthenticationError(RoutingLayerError):
    """Raised when an API key is missing or invalid."""

    http_status = 401
    error_code = "authentication_error"


class AuthorisationError(RoutingLayerError):
    """Raised when a key lacks permission for the requested operation."""

    http_status = 403
    error_code = "authorisation_error"


class ModelNotAllowedError(AuthorisationError):
    """Phase 1 — Task 1.3: Raised when a model is not in the key's whitelist."""

    error_code = "model_not_allowed"


# ── Rate Limiting & Quotas ───────────────────────────────────────────────────

class RateLimitError(RoutingLayerError):
    """Raised when a rate limit is exceeded."""

    http_status = 429
    error_code = "rate_limit_exceeded"


class BudgetExceededError(RoutingLayerError):
    """Phase 1 — Task 1.2: Raised when the monthly budget cap is reached."""

    http_status = 429
    error_code = "monthly_budget_exceeded"


# ── Routing ──────────────────────────────────────────────────────────────────

class NoProvidersAvailableError(RoutingLayerError):
    """Raised when no provider can fulfil the request."""

    http_status = 503
    error_code = "no_providers_available"


class DataPolicyViolationError(RoutingLayerError):
    """Phase 3 — Task 3.4: Raised when no ZDR-compliant provider is available."""

    http_status = 422
    error_code = "data_policy_violation"


# ── Provider ─────────────────────────────────────────────────────────────────

class ProviderError(RoutingLayerError):
    """Raised when an upstream LLM provider returns an error."""

    http_status = 502
    error_code = "provider_error"

    def __init__(
        self,
        message: str,
        provider: str,
        retriable: bool = False,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, details)
        self.provider = provider
        self.retriable = retriable


class ProviderCircuitOpenError(ProviderError):
    """Raised when a provider's circuit breaker is in the OPEN state."""

    error_code = "circuit_open"


# ── Validation ───────────────────────────────────────────────────────────────

class SchemaValidationError(RoutingLayerError):
    """Phase 4 — Task 4.4: Raised when structured output fails JSON Schema validation."""

    http_status = 422
    error_code = "schema_validation_failed"


__all__ = [
    "RoutingLayerError",
    "AuthenticationError",
    "AuthorisationError",
    "ModelNotAllowedError",
    "RateLimitError",
    "BudgetExceededError",
    "NoProvidersAvailableError",
    "DataPolicyViolationError",
    "ProviderError",
    "ProviderCircuitOpenError",
    "SchemaValidationError",
]
