"""Cross-service contract tests for the Solvable AI platform.

These tests deliberately exercise only canonical shared models and deterministic
fixtures. They do not call production services or external providers.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from ai_routing_shared.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    UsageRecord,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "platform_fixture.json"


@pytest.fixture(scope="module")
def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.contract
def test_chat_request_round_trips_with_provider_policy(fixture: dict) -> None:
    payload = {**fixture["chat"], "provider": fixture["routing"]}
    request = ChatCompletionRequest.model_validate(payload)

    assert request.model == "gpt-4o-mini"
    assert request.messages[0].role == "system"
    assert request.provider is not None
    assert request.provider.data_collection == "deny"
    assert request.provider.allow_fallbacks is True
    assert request.model_dump(mode="json")["provider"]["order"] == [
        "openai",
        "qwen",
        "mistral",
    ]


@pytest.mark.contract
def test_embedding_request_supports_batch_inputs(fixture: dict) -> None:
    request = EmbeddingRequest.model_validate(fixture["embedding"])

    assert isinstance(request.input, list)
    assert len(request.input) == 2
    assert request.model == "text-embedding-3-small"


@pytest.mark.contract
def test_normalized_completion_schema_is_provider_independent() -> None:
    response = ChatCompletionResponse.model_validate(
        {
            "id": "chatcmpl_release_0001",
            "created": 1_756_000_000,
            "model": "gpt-4o-mini",
            "provider": "qwen",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "READY"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 8,
                "completion_tokens": 1,
                "total_tokens": 9,
                "estimated_cost_usd": 0.0001,
            },
            "generation_id": "gen_release_0001",
        }
    )

    assert response.object == "chat.completion"
    assert response.choices[0].message.content == "READY"
    assert response.usage.total_tokens == 9
    assert response.generation_id == "gen_release_0001"


@pytest.mark.contract
def test_stream_chunk_schema_and_sse_contract() -> None:
    chunk = ChatCompletionChunk.model_validate(
        {
            "id": "chatcmpl_release_0001",
            "created": 1_756_000_000,
            "model": "gpt-4o-mini",
            "provider": "openai",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "READY"},
                    "finish_reason": None,
                }
            ],
        }
    )
    sse_line = f"data: {chunk.model_dump_json()}"

    assert chunk.object == "chat.completion.chunk"
    assert sse_line.startswith("data: {")
    assert json.loads(sse_line.removeprefix("data: "))["choices"][0]["delta"]["content"] == "READY"


@pytest.mark.contract
def test_usage_record_is_billing_compatible(fixture: dict) -> None:
    record = UsageRecord.model_validate(fixture["usage"])
    serialized = record.model_dump(mode="json")

    assert serialized["id"] == "gen_release_0001"
    assert serialized["total_tokens"] == 11
    assert serialized["billed_usd"] > serialized["cost_usd"]
    assert isinstance(serialized["created_at"], str)


@pytest.mark.contract
def test_fixture_is_secret_free_and_locale_complete(fixture: dict) -> None:
    assert fixture["locales"] == ["uz", "ru", "en"]
    assert fixture["user"]["email"].endswith(".invalid")
    assert fixture["api_key"]["raw"].startswith("sk-test-")
    assert fixture["api_key"]["raw"] != fixture["api_key"]["id"]
