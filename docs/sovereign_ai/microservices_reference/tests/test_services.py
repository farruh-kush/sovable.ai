from __future__ import annotations

from fastapi.testclient import TestClient

from services.auth.app import app as auth_app
from services.billing.app import app as billing_app
from services.provider.app import app as provider_app
from services.router.app import app as router_app
from shared.privacy import PrivacyEngine


SECRET = "local-dev-internal-secret"


def test_privacy_round_trip() -> None:
    engine = PrivacyEngine()
    masked, mapping, entities = engine.mask_text("Email alice@example.com and PINFL 12345678901234.")
    assert "<EMAIL_1>" in masked
    assert "<PINFL_1>" in masked
    assert len(entities) == 2
    assert engine.restore_text(masked, mapping) == "Email alice@example.com and PINFL 12345678901234."


def test_auth_requires_internal_secret_and_valid_key() -> None:
    client = TestClient(auth_app)
    missing = client.post("/internal/authorize", json={"api_key": "sk-local-demo"})
    assert missing.status_code == 401
    valid = client.post(
        "/internal/authorize",
        headers={"X-Internal-Secret": SECRET},
        json={"api_key": "sk-local-demo", "required_scope": "chat:complete"},
    )
    assert valid.status_code == 200
    assert valid.json()["principal"]["organization_id"] == "demo-org"


def test_router_enforces_external_policy() -> None:
    client = TestClient(router_app)
    payload = {
        "request_id": "r1",
        "requested_model": "gpt-4o-mini",
        "principal": {
            "api_key_id": "key",
            "subject": "user",
            "organization_id": "org",
            "tier": "paid",
            "scopes": ["chat:complete"],
        },
        "allow_external": False,
        "estimated_tokens": 10,
    }
    denied = client.post("/internal/route", headers={"X-Internal-Secret": SECRET}, json=payload)
    assert denied.status_code == 403
    payload["allow_external"] = True
    allowed = client.post("/internal/route", headers={"X-Internal-Secret": SECRET}, json=payload)
    assert allowed.status_code == 200
    assert allowed.json()["unit_cost_usd_per_1k"] == 0.003


def test_provider_fake_contract_returns_openai_shape() -> None:
    client = TestClient(provider_app)
    body = {
        "request_id": "r2",
        "route": {
            "provider": "local-fake",
            "provider_model": "local-fake",
            "endpoint": "http://127.0.0.1:8103",
            "fallback_chain": [],
            "reason": "local residency policy",
            "unit_cost_usd_per_1k": 0.0005,
            "estimated_cost_usd": 0.001,
        },
        "chat": {
            "model": "local",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "metadata": {},
        },
    }
    response = client.post("/internal/chat", headers={"X-Internal-Secret": SECRET}, json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["response"]["object"] == "chat.completion"
    assert result["input_tokens"] > 0


def test_billing_usage_is_idempotent() -> None:
    client = TestClient(billing_app)
    body = {
        "request_id": "billing-test-idempotent",
        "principal": {
            "api_key_id": "key",
            "subject": "user",
            "organization_id": "billing-test-org",
            "tier": "paid",
            "scopes": [],
        },
        "provider": "local-fake",
        "model": "local-fake",
        "input_tokens": 2,
        "output_tokens": 2,
        "latency_ms": 1,
        "estimated_cost_usd": 1.25,
    }
    first = client.post("/internal/usage", headers={"X-Internal-Secret": SECRET}, json=body)
    second = client.post("/internal/usage", headers={"X-Internal-Secret": SECRET}, json=body)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["monthly_cost_usd"] == second.json()["monthly_cost_usd"]
