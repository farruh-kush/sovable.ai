from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: bool = False
    user: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]
    user: Optional[str] = None


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    provider: str
    choices: list[ChatChoice]
    usage: UsageInfo


class ChatCompletionChunkDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    provider: str
    choices: list[ChatCompletionChunkChoice]


class EmbeddingVector(BaseModel):
    object: str = "embedding"
    index: int
    embedding: list[float]


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingVector]
    model: str
    provider: str
    usage: UsageInfo


class ProviderErrorPayload(BaseModel):
    code: str
    message: str
    provider: Optional[str] = None
    retriable: bool = False


class ProviderResult(BaseModel):
    response: Optional[Union[ChatCompletionResponse, EmbeddingResponse]] = None
    stream: Optional[Any] = None
    usage: UsageInfo = Field(default_factory=UsageInfo)


class UsageRecord(BaseModel):
    request_id: str
    api_key_id: str
    user_id: str
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


__all__ = [
    "ChatMessage",
    "ChatCompletionRequest",
    "EmbeddingRequest",
    "UsageInfo",
    "ChatChoice",
    "ChatCompletionResponse",
    "ChatCompletionChunkDelta",
    "ChatCompletionChunkChoice",
    "ChatCompletionChunk",
    "EmbeddingVector",
    "EmbeddingResponse",
    "ProviderErrorPayload",
    "ProviderResult",
    "UsageRecord",
]
