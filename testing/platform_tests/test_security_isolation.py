"""Static security and isolation checks that run without production access."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from ai_routing_shared.models import ChatMessage
from ai_routing_shared.privacy import mask_chat_messages

ROOT = Path(__file__).parents[2]
SERVICE_ROOT = ROOT / "microservices"


def _source_files() -> list[Path]:
    excluded = {"__pycache__", ".pytest_cache", "node_modules", ".next", "out", "venv", ".venv", "evidence"}
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml", ".md", ".json"}
        and not any(part in excluded for part in path.parts)
        and path.name not in {".env", ".env.local", ".env.production"}
    ]


@pytest.mark.security
def test_sensitive_text_is_masked_at_provider_boundary() -> None:
    original_email = "release.user@example.invalid"
    original_phone = "+998 90 123 45 67"
    messages = [
        ChatMessage(
            role="user",
            content=f"Email {original_email}; phone {original_phone}; do not persist.",
        )
    ]

    masked, session = mask_chat_messages(messages)
    masked_text = str(masked[0].content)

    assert original_email not in masked_text
    assert original_phone not in masked_text
    assert "<PII_EMAIL_" in masked_text
    assert "<PII_PHONE_" in masked_text
    assert session.restore_text(masked_text) == str(messages[0].content)


@pytest.mark.security
def test_privacy_preview_contract_does_not_return_original_values() -> None:
    source = (SERVICE_ROOT / "router/src/router/api/__init__.py").read_text(encoding="utf-8")

    assert '"restoration": "request-local; original values are not returned by this endpoint"' in source
    assert "mask_chat_messages" in source
    assert "provider_boundary" in source


@pytest.mark.security
def test_no_service_uses_another_service_database() -> None:
    forbidden_by_service = {
        "gateway": ("auth_db", "billing_db", "asyncpg", "sqlalchemy"),
        "router": ("auth_db", "billing_db", "asyncpg", "sqlalchemy"),
        "provider": ("auth_db", "billing_db", "asyncpg", "sqlalchemy"),
    }
    for service, forbidden in forbidden_by_service.items():
        service_dir = SERVICE_ROOT / service / "src"
        text = "\n".join(path.read_text(encoding="utf-8") for path in service_dir.rglob("*.py"))
        for needle in forbidden:
            assert needle not in text, f"{service} must not access database concern {needle!r}"


@pytest.mark.security
def test_peer_services_are_http_boundaries() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "PROVIDER_SERVICE_URL: \"http://provider:8003\"" in compose
    assert "BILLING_SERVICE_URL: \"http://billing:8004\"" in compose
    assert "DATABASE_URL: \"postgresql+asyncpg://" in compose
    assert "BILLING_DATABASE_URL: \"postgresql+asyncpg://" in compose


@pytest.mark.security
def test_no_high_confidence_secret_literals_in_source_or_docs() -> None:
    secret_patterns = (
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
        re.compile(r"\bsk-[A-Za-z0-9]{24,}\b"),
        re.compile(r"\b(?:xox[baprs]-|ghp_)[A-Za-z0-9_-]{20,}\b"),
    )
    findings: list[str] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in secret_patterns:
            if pattern.search(text):
                findings.append(str(path.relative_to(ROOT)))
                break
    assert not findings, "Potential secret literals found: " + ", ".join(sorted(findings))


@pytest.mark.security
def test_ack_overlay_keeps_runtime_secrets_externalized() -> None:
    template = (ROOT / "infrastructure/k8s/base/secrets.yaml.template").read_text(encoding="utf-8")
    example = (ROOT / "infrastructure/k8s/overlays/alibaba/secrets.example.env").read_text(encoding="utf-8")

    assert "REPLACE_WITH_SCOPED_" in template
    assert "Never commit actual keys to Git." in example
    assert "openai-api-key=" in example


@pytest.mark.security
def test_frontend_has_portal_and_language_surface() -> None:
    frontend = ROOT / "frontend/dashboard"
    source = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in frontend.rglob("*")
        if path.is_file() and path.suffix in {".tsx", ".ts", ".jsx", ".js"}
        and "node_modules" not in path.parts
        and ".next" not in path.parts
        and "out" not in path.parts
    )
    assert "/portal" in source
    assert "creator" in source.lower()
    assert "agent" in source.lower()
    for locale in ("uz", "ru", "en"):
        assert locale in source.lower()
