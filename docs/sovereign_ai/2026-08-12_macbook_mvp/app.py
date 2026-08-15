from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from privacy import PrivacyEngine
from provider import Provider, ProviderError


class ChatCompletionRequest(BaseModel):
    model: str = "local"
    messages: list[dict[str, Any]] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    metadata: dict[str, Any] | None = None


class InspectRequest(BaseModel):
    text: str


privacy = PrivacyEngine()
provider = Provider()
app = FastAPI(
    title="MacBook Sovereign AI Gateway MVP",
    version="0.1.0",
    description="Local privacy boundary with OpenAI-compatible chat completions.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "provider_mode": provider.mode}


@app.post("/v1/privacy/inspect")
async def inspect(request: InspectRequest) -> dict[str, Any]:
    return privacy.inspect(request.text)


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming is intentionally deferred in this MVP")

    request_payload = request.model_dump(exclude_none=True)
    masked_messages, mapping, entities = privacy.mask_messages(request.messages)
    request_payload["messages"] = masked_messages

    try:
        response = await provider.chat(request_payload)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    restored_response = privacy.restore_payload(response, mapping)
    if isinstance(restored_response, dict):
        restored_response.setdefault("x_privacy", {})
        restored_response["x_privacy"].update(
            {
                "masked_entity_count": len(entities),
                "entity_types": sorted({entity.entity_type for entity in entities}),
                "provider_mode": provider.mode,
            }
        )
    return restored_response
