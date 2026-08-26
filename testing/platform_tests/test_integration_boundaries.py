"""Cross-service integration boundary checks without real service mutation."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


@pytest.mark.integration
def test_gateway_calls_auth_and_router_over_http_contracts() -> None:
    auth = read("microservices/gateway/src/gateway/core/auth.py")
    downstream = read("microservices/gateway/src/gateway/core/downstream.py")
    chat = read("microservices/gateway/src/gateway/api/v1/chat.py")

    assert '"/internal/validate-key"' in auth
    assert "client.request(method, path" in downstream
    assert '"/route/chat/completions"' in chat
    assert "request_peer" in chat
    assert "response_error_or_none" in chat


@pytest.mark.integration
def test_router_calls_provider_and_billing_as_separate_peers() -> None:
    engine = read("microservices/router/src/router/engine/routing_engine.py")
    config = read("microservices/router/src/router/core/config.py")

    assert "provider_service_url" in config
    assert "billing_service_url" in config
    assert '"/adapt/chat/completions"' in engine
    assert '"/adapt/embeddings"' in engine
    assert '"/internal/usage"' in engine
    assert "Billing is best-effort" in engine


@pytest.mark.integration
@pytest.mark.resilience
def test_retry_timeout_fallback_and_circuit_controls_are_present() -> None:
    router_engine = read("microservices/router/src/router/engine/routing_engine.py")
    provider_base = read("microservices/provider/src/provider/adapters/base.py")
    provider_boundary = read("microservices/provider/tests/test_provider_boundary.py")

    assert "fallback" in router_engine.lower()
    assert "timeout" in router_engine.lower()
    assert "retriable" in provider_base
    assert "circuit" in provider_base.lower()
    assert "test_timeout_retries_then_classifies" in provider_boundary
    assert "test_outage_opens_circuit_after_failure_budget" in provider_boundary


@pytest.mark.integration
def test_billing_usage_contract_contains_cost_and_quota_dimensions() -> None:
    usage = read("microservices/billing/src/billing/api/usage.py")
    pricing = read("microservices/billing/src/billing/pricing/catalog.py")
    gateway_auth = read("microservices/gateway/src/gateway/core/auth.py")

    for field in ("prompt_tokens", "completion_tokens", "billed_usd", "latency_ms", "fallback_used"):
        assert field in usage
    assert "platform_markup" in usage
    assert "calculate" in pricing
    assert "monthly_budget_usd" in gateway_auth
    assert "BudgetExceededError" in gateway_auth


@pytest.mark.integration
@pytest.mark.security
def test_admin_and_user_boundaries_are_explicit() -> None:
    gateway_admin = read("microservices/gateway/src/gateway/api/v1/admin.py")
    auth_identity = read("microservices/auth/src/auth/api/identity.py")
    auth_keys = read("microservices/auth/src/auth/api/keys.py")

    assert "require_admin" in gateway_admin or "admin" in gateway_admin.lower()
    assert "RoleUpdateRequest" in auth_identity
    assert "require_admin" in auth_identity or "admin" in auth_identity.lower()
    assert "api_key" in auth_keys.lower()


@pytest.mark.integration
def test_mock_provider_is_local_only_and_has_all_provider_contracts() -> None:
    mock = read("testing/mocks/provider_mock.py")

    assert "ThreadingHTTPServer" in mock
    assert "MOCK_PROVIDER_MODE" in mock
    assert '"/embeddings"' in mock
    assert '"stream"' in mock
    assert "serve_forever" in mock
    assert "api.openai.com" not in mock
