from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException

from shared.config import settings
from shared.models import HealthResponse, ProviderChatRequest, ProviderChatResponse


config = settings("provider", 8103)
app = FastAPI(title="AI Routing Provider Service", version="0.1.0")
PROVIDER_MODE = os.getenv("PROVIDER_MODE", "fake").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))


def require_internal(secret: str | None) -> None:
    if secret != config.internal_secret:
        raise HTTPException(status_code=401, detail="invalid internal service credential")


def content_text(messages: list[dict[str, Any]]) -> str:
    values: list[str] = []
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            values.append(content)
        elif isinstance(content, list):
            values.extend(part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text")
    return " ".join(value for value in values if value)


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def fake_completion(payload: ProviderChatRequest) -> tuple[dict[str, Any], int, int]:
    masked_text = content_text([message.model_dump() for message in payload.chat.messages])
    response_text = f"[{payload.route.provider}] routed model {payload.route.provider_model}: {masked_text}"
    input_tokens = estimate_tokens(masked_text)
    output_tokens = estimate_tokens(response_text)
    return (
        {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.route.provider_model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        },
        input_tokens,
        output_tokens,
    )


async def ollama_completion(payload: ProviderChatRequest) -> tuple[dict[str, Any], int, int]:
    request = payload.chat.model_dump(exclude_none=True)
    request["model"] = payload.route.provider_model
    request["stream"] = False
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/chat/completions",
                headers={"Authorization": "Bearer ollama"},
                json=request,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama provider failed: {exc}") from exc
    usage = body.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens", 0))
    output_tokens = int(usage.get("completion_tokens", 0))
    return body, input_tokens, output_tokens


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=config.service_name, status="ok")


@app.post("/internal/chat", response_model=ProviderChatResponse)
async def chat(payload: ProviderChatRequest, x_internal_secret: str | None = Header(default=None)) -> ProviderChatResponse:
    require_internal(x_internal_secret)
    started = time.perf_counter()
    if PROVIDER_MODE == "ollama" and payload.route.provider in {"local-fake", "local-ollama"}:
        body, input_tokens, output_tokens = await ollama_completion(payload)
    else:
        body, input_tokens, output_tokens = fake_completion(payload)
    latency_ms = max(1, int((time.perf_counter() - started) * 1000))
    return ProviderChatResponse(
        response=body,
        provider=payload.route.provider,
        model=payload.route.provider_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        estimated_cost_usd=round((input_tokens + output_tokens) / 1000 * payload.route.unit_cost_usd_per_1k, 6),
    )
