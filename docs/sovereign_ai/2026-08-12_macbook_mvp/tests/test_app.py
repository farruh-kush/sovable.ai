from __future__ import annotations

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["provider_mode"] == "fake"


def test_privacy_inspection_detects_local_identifier_patterns() -> None:
    response = client.post(
        "/v1/privacy/inspect",
        json={"text": "Email me at alice@example.com; PINFL 12345678901234."},
    )
    assert response.status_code == 200
    body = response.json()
    assert "<EMAIL_1>" in body["masked_text"]
    assert "<PINFL_1>" in body["masked_text"]
    assert {entity["type"] for entity in body["entities"]} == {"EMAIL", "PINFL"}


def test_chat_masks_before_provider_and_restores_in_response() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "local",
            "messages": [
                {"role": "user", "content": "Send a receipt to alice@example.com."},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "alice@example.com" in body["choices"][0]["message"]["content"]
    assert "<EMAIL_1>" not in body["choices"][0]["message"]["content"]
    assert body["x_privacy"]["masked_entity_count"] == 1


def test_chat_rejects_streaming_until_implemented() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "local",
            "stream": True,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 400
    assert "deferred" in response.json()["detail"]


def test_multimodal_text_parts_are_masked() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "local",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Call +998 90 123 45 67."},
                        {"type": "text", "text": "No sensitive data here."},
                    ],
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "+998 90 123 45 67" in body["choices"][0]["message"]["content"]
    assert body["x_privacy"]["masked_entity_count"] == 1
