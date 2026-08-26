"""Release-surface tests for the complete platform contract."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from ai_routing_shared.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    DataPolicyViolationError,
    ModelNotAllowedError,
    NoProvidersAvailableError,
    ProviderCircuitOpenError,
    RateLimitError,
    UpstreamTimeoutError,
)

ROOT = Path(__file__).parents[2]


@pytest.mark.contract
def test_each_microservice_exposes_a_health_or_adapter_health_route() -> None:
    expected = {
        "gateway": "@router.get(\"/health\")",
        "auth": "@app.get(\"/health\")",
        "router": "@app.get(\"/health\")",
        "provider": "@router.get(\"/health\")",
        "billing": "@app.get(\"/health\")",
    }
    for service, marker in expected.items():
        sources = list((ROOT / "microservices" / service / "src").rglob("*.py"))
        text = "\n".join(path.read_text(encoding="utf-8") for path in sources)
        assert marker in text, service


@pytest.mark.contract
def test_required_route_families_are_present() -> None:
    required = {
        "gateway": (
            "/chat/completions",
            "/embeddings",
            "/privacy",
            "/generations",
            "/keys",
        ),
        "auth": (
            "/register/",
            "/email/activation/start",
            "/email/activation/complete",
            "/login",
            "/refresh",
            "/logout",
        ),
        "router": ("/chat/completions", "/embeddings", "/privacy/preview", "/models"),
        "provider": ("/chat/completions", "/embeddings", "/capabilities"),
        "billing": ("/usage", "/generations/", "/usage/monthly/"),
    }
    for service, routes in required.items():
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "microservices" / service / "src").rglob("*.py")
        )
        for route in routes:
            assert route in text, f"{service} missing route family {route}"


@pytest.mark.contract
def test_failure_taxonomy_has_stable_status_and_code() -> None:
    cases = (
        (AuthenticationError("bad key"), 401, "authentication_error"),
        (ModelNotAllowedError("not allowed"), 403, "model_not_allowed"),
        (RateLimitError("too many"), 429, "rate_limit_exceeded"),
        (BudgetExceededError("budget"), 429, "monthly_budget_exceeded"),
        (NoProvidersAvailableError("none"), 503, "no_providers_available"),
        (DataPolicyViolationError("policy"), 422, "data_policy_violation"),
        (ProviderCircuitOpenError("open", provider="openai"), 502, "circuit_open"),
        (UpstreamTimeoutError("slow", service="router"), 504, "upstream_timeout"),
    )
    for error, status, code in cases:
        assert error.http_status == status
        assert error.error_code == code
        assert str(error)


@pytest.mark.contract
def test_route_modules_are_valid_python_and_use_shared_contracts() -> None:
    route_files = [
        ROOT / "microservices" / service / "src"
        for service in ("gateway", "auth", "router", "provider", "billing")
    ]
    parsed = 0
    for source_root in route_files:
        for path in source_root.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            parsed += 1
    assert parsed >= 30


@pytest.mark.contract
def test_frontend_route_inventory_covers_required_user_boundaries() -> None:
    pages = ROOT / "frontend/dashboard/pages"
    routes = {str(path.relative_to(pages)).replace(".tsx", "") for path in pages.rglob("*.tsx")}
    expected = {
        "portal",
        "portal/login",
        "portal/register",
        "app-store",
        "creator",
        "creator/login",
        "creator/register",
        "admin",
        "admin/login",
        "dashboard/keys",
        "dashboard/playground",
        "auth/activate",
    }
    assert expected.issubset(routes)


@pytest.mark.contract
def test_routing_config_is_present_and_has_fallback_or_candidate_policy() -> None:
    routing = (ROOT / "ai/config/routing.yaml").read_text(encoding="utf-8")
    assert "routing:" in routing
    assert "pricing:" in routing
    assert "fallback:" in routing or "candidates:" in routing
    assert "openai" in routing
    assert "qwen" in routing or "mistral" in routing
