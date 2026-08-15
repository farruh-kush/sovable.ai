from __future__ import annotations

import os
from typing import Any

import httpx


class ProviderError(RuntimeError):
    pass


class Provider:
    def __init__(self) -> None:
        self.mode = os.getenv("PROVIDER_MODE", "fake").lower()
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

    async def chat(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "fake":
            return self._fake_response(request)
        if self.mode == "ollama":
            return await self._ollama_response(request)
        raise ProviderError(f"Unsupported PROVIDER_MODE={self.mode!r}; use fake or ollama")

    @staticmethod
    def _fake_response(request: dict[str, Any]) -> dict[str, Any]:
        messages = request.get("messages") or []
        last_user = next(
            (message.get("content", "") for message in reversed(messages) if message.get("role") == "user"),
            "",
        )
        if not isinstance(last_user, str):
            last_user = str(last_user)
        content = f"[fake-provider] received: {last_user}"
        return {
            "id": "chatcmpl-local-fake",
            "object": "chat.completion",
            "created": 0,
            "model": request.get("model", "local-fake"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    async def _ollama_response(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = dict(request)
        payload["model"] = request.get("model") or self.model
        payload["stream"] = False
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": "Bearer ollama"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Ollama request failed at {self.base_url}. Is Ollama running and is the model pulled?"
            ) from exc
