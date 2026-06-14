from fastapi.testclient import TestClient

from ai_routing_layer.main import app

client = TestClient(app)


def test_chat_completions_success() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer dev-default-key"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] in {"openai", "anthropic"}
    assert body["choices"][0]["message"]["content"]
    assert body["usage"]["estimated_cost_usd"] > 0


def test_chat_completions_streaming() -> None:
    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers={"Authorization": "Bearer dev-default-key"},
        json={
            "model": "gpt-4o-mini",
            "stream": True,
            "messages": [{"role": "user", "content": "Stream this"}],
        },
    ) as response:
        assert response.status_code == 200
        text = "".join(response.iter_text())
        assert "data: " in text
        assert "[DONE]" in text


def test_invalid_api_key_rejected() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer invalid"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.status_code == 401


def test_embeddings_success() -> None:
    response = client.post(
        "/v1/embeddings",
        headers={"Authorization": "Bearer dev-default-key"},
        json={"model": "gpt-4o-mini", "input": "embed me"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["embedding"]
    assert body["usage"]["prompt_tokens"] > 0
