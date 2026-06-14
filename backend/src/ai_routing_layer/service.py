from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException, status

from ai_routing_layer.auth.service import Principal
from ai_routing_layer.billing.service import BillingService
from ai_routing_layer.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    UsageRecord,
)
from ai_routing_layer.observability.metrics import MetricsRegistry
from ai_routing_layer.providers.base import ProviderError
from ai_routing_layer.router.engine import RoutingEngine


class RoutingService:
    def __init__(
        self,
        router: RoutingEngine,
        billing: BillingService,
        metrics: MetricsRegistry,
    ) -> None:
        self.router = router
        self.billing = billing
        self.metrics = metrics

    async def create_chat_completion(
        self,
        request: ChatCompletionRequest,
        principal: Principal,
    ) -> ChatCompletionResponse:
        self.billing.enforce_quota(principal.api_key_id, principal.daily_quota_usd)
        errors: list[str] = []
        for provider in self.router.candidates_for_model(request.model):
            timer = self.metrics.request_latency_seconds.labels("/v1/chat/completions", provider.name).time()
            with timer:
                try:
                    response = await provider.chat(request)
                    response.usage = self.billing.enrich_usage(provider.name, request.model, response.usage)
                    self._record_usage(response.id, principal, request.model, provider.name, response.usage)
                    self.metrics.provider_requests_total.labels(provider.name, "success").inc()
                    return response
                except ProviderError as exc:
                    errors.append(f"{provider.name}: {exc.payload.message}")
                    self.metrics.request_errors_total.labels("/v1/chat/completions", provider.name).inc()
                    self.metrics.provider_requests_total.labels(provider.name, "error").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"All providers failed: {'; '.join(errors)}",
        )

    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        principal: Principal,
    ) -> AsyncIterator[str]:
        self.billing.enforce_quota(principal.api_key_id, principal.daily_quota_usd)
        provider = self.router.candidates_for_model(request.model)[0]
        request_id = f"chatcmpl-{uuid.uuid4().hex}"
        collected_text = []
        async for chunk in provider.chat_stream(request):
            collected_text.extend(
                choice.delta.content for choice in chunk.choices if choice.delta.content
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
        prompt_tokens = sum(provider.estimate_tokens(message.content) for message in request.messages)
        completion_tokens = provider.estimate_tokens("".join(collected_text))
        usage = self.billing.enrich_usage(
            provider.name,
            request.model,
            chunk_usage(prompt_tokens, completion_tokens),
        )
        self._record_usage(request_id, principal, request.model, provider.name, usage)
        yield "data: [DONE]\n\n"

    async def create_embedding(
        self,
        request: EmbeddingRequest,
        principal: Principal,
    ) -> EmbeddingResponse:
        self.billing.enforce_quota(principal.api_key_id, principal.daily_quota_usd)
        provider = self.router.candidates_for_model(request.model)[0]
        response = await provider.embeddings(request)
        response.usage = self.billing.enrich_usage(provider.name, request.model, response.usage)
        self._record_usage(
            request_id=f"emb-{uuid.uuid4().hex}",
            principal=principal,
            model=request.model,
            provider=provider.name,
            usage=response.usage,
        )
        return response

    def _record_usage(self, request_id: str, principal: Principal, model: str, provider: str, usage) -> None:
        self.billing.record(
            UsageRecord(
                request_id=request_id,
                api_key_id=principal.api_key_id,
                user_id=principal.user_id,
                model=model,
                provider=provider,
                tokens_in=usage.prompt_tokens,
                tokens_out=usage.completion_tokens,
                cost_usd=usage.estimated_cost_usd,
            )
        )


def chunk_usage(prompt_tokens: int, completion_tokens: int):
    from ai_routing_layer.models import UsageInfo

    return UsageInfo(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
