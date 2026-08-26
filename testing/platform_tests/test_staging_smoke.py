"""Opt-in staging smoke tests.

Nothing in this module runs against a default or production endpoint. Set
PLATFORM_TARGET_ENV=staging and the corresponding *_BASE_URL variables to run.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "platform_fixture.json"


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _staging_url(name: str) -> str:
    if os.getenv("PLATFORM_TARGET_ENV") != "staging":
        pytest.skip("staging smoke is opt-in; set PLATFORM_TARGET_ENV=staging")
    url = os.getenv(name)
    if not url:
        pytest.skip(f"{name} is not configured")
    host = (urlparse(url).hostname or "").lower()
    if host in {"api.sovable.ai", "sovable.ai", "www.sovable.ai"}:
        pytest.fail("staging smoke refuses production host")
    return url.rstrip("/")


@pytest.mark.staging
@pytest.mark.asyncio
async def test_staging_health_matrix() -> None:
    raw = os.getenv("PLATFORM_HEALTH_URLS")
    if not raw:
        pytest.skip("PLATFORM_HEALTH_URLS is not configured")
    if os.getenv("PLATFORM_TARGET_ENV") != "staging":
        pytest.skip("staging smoke is opt-in; set PLATFORM_TARGET_ENV=staging")

    targets = dict(item.split("=", 1) for item in raw.split(",") if "=" in item)
    assert targets, "PLATFORM_HEALTH_URLS must contain name=url entries"
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in targets.items():
            parsed = urlparse(url)
            assert parsed.hostname not in {"api.sovable.ai", "sovable.ai", "www.sovable.ai"}, name
            response = await client.get(url)
            assert response.status_code == 200, f"{name} health returned {response.status_code}"
            payload = response.json()
            assert payload.get("status") == "healthy", name
            assert payload.get("service"), name


@pytest.mark.staging
@pytest.mark.asyncio
async def test_staging_gateway_core_paths() -> None:
    gateway = _staging_url("GATEWAY_BASE_URL")
    api_key = os.getenv("PLATFORM_TEST_API_KEY")
    if not api_key:
        pytest.skip("PLATFORM_TEST_API_KEY is not configured")
    fixture = _fixture()
    headers = {"Authorization": f"Bearer {api_key}", "X-Request-ID": fixture["request_id"]}
    async with httpx.AsyncClient(base_url=gateway, timeout=30.0) as client:
        chat = await client.post("/v1/chat/completions", json=fixture["chat"], headers=headers)
        assert chat.status_code == 200
        body = chat.json()
        assert body["object"] == "chat.completion"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["usage"]["total_tokens"] >= 0
        assert chat.headers.get("x-request-id") or chat.headers.get("X-Request-ID")

        embeddings = await client.post("/v1/embeddings", json=fixture["embedding"], headers=headers)
        assert embeddings.status_code == 200
        embedding_body = embeddings.json()
        assert embedding_body["object"] == "list"
        assert len(embedding_body["data"]) == len(fixture["embedding"]["input"])

        stream = await client.post("/v1/chat/completions", json=fixture["stream_chat"], headers=headers)
        assert stream.status_code == 200
        assert stream.headers["content-type"].startswith("text/event-stream")
        assert "[DONE]" in stream.text


@pytest.mark.staging
@pytest.mark.asyncio
async def test_staging_privacy_preview_and_locale_portals() -> None:
    gateway = _staging_url("GATEWAY_BASE_URL")
    fixture = _fixture()
    sensitive = "release.user@example.invalid"
    async with httpx.AsyncClient(base_url=gateway, timeout=15.0) as client:
        response = await client.post(
            "/v1/privacy/preview",
            json={"messages": [{"role": "user", "content": f"Email {sensitive}"}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert sensitive not in response.text
        assert body["detected_count"] >= 1
        assert body["restoration"].startswith("request-local")

    dashboard = os.getenv("DASHBOARD_BASE_URL")
    if not dashboard:
        pytest.skip("DASHBOARD_BASE_URL is not configured")
    if urlparse(dashboard).hostname in {"sovable.ai", "www.sovable.ai"}:
        pytest.fail("staging smoke refuses production host")
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for locale in fixture["locales"]:
            response = await client.get(f"{dashboard.rstrip('/')}/portal?lang={locale}")
            assert response.status_code < 400, locale
            assert "Solvable" in response.text, locale


@pytest.mark.staging
@pytest.mark.asyncio
async def test_staging_auth_activation_is_explicitly_enabled() -> None:
    auth = _staging_url("AUTH_BASE_URL")
    if os.getenv("RUN_MUTATING_STAGING_SMOKE") != "1":
        pytest.skip("activation creates test state; set RUN_MUTATING_STAGING_SMOKE=1")
    fixture = _fixture()
    async with httpx.AsyncClient(base_url=auth, timeout=15.0) as client:
        response = await client.post(
            "/auth/email/activation/start",
            json={
                "email": fixture["user"]["email"],
                "display_name": fixture["user"]["display_name"],
                "account_type": "user",
            },
        )
        assert response.status_code in {200, 202}
        assert "token" not in response.text.lower()


@pytest.mark.staging
@pytest.mark.asyncio
async def test_staging_billing_usage_is_explicitly_enabled() -> None:
    billing = _staging_url("BILLING_BASE_URL")
    if os.getenv("RUN_MUTATING_STAGING_SMOKE") != "1":
        pytest.skip("usage ingestion creates billing state; set RUN_MUTATING_STAGING_SMOKE=1")
    fixture = _fixture()
    async with httpx.AsyncClient(base_url=billing, timeout=15.0) as client:
        response = await client.post("/internal/usage", json=fixture["usage"])
        assert response.status_code == 202
        assert response.json().get("status") == "accepted"
