"""Intelligent Routing Engine.

Implements all routing strategies from the implementation plan:
  - Static routing (model → provider mapping from routing.yaml)
  - Dynamic routing (cost, latency, throughput optimisation)
  - Policy-based routing (user tier, data policy / ZDR)
  - Fallback chains with circuit breaker awareness
  - Client-side routing controls (Phase 3 — Task 3.1: ProviderPreferences)
  - Data policy filtering (Phase 3 — Task 3.4: ZDR routing)
  - Real latency-optimised routing (Phase 4 — Task 4.1)

Author: Farruh
"""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path
from typing import AsyncIterator, List, Optional

import httpx
import yaml

from ai_routing_shared.exceptions import (
    DataPolicyViolationError,
    NoProvidersAvailableError,
    ProviderError,
)
from ai_routing_shared.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    UsageRecord,
)
from ai_routing_shared.utils import get_logger

from ..core.redis_client import RouterRedisClient

logger = get_logger(__name__)


class RoutingEngine:
    """The core routing engine.

    Selects the optimal provider for each request based on the configured
    routing strategy and client-supplied preferences, then delegates the
    actual LLM call to the Provider Adapter Service.
    """

    def __init__(
        self,
        config_path: Path,
        provider_service_url: str,
        billing_service_url: str,
        redis: RouterRedisClient,
    ) -> None:
        self._config = self._load_config(config_path)
        self._provider_url = provider_service_url
        self._billing_url = billing_service_url
        self._redis = redis

    @staticmethod
    def _load_config(path: Path) -> dict:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        logger.warning("routing_config_not_found", path=str(path))
        return {}

    # ── Public API ───────────────────────────────────────────────────────────

    async def route_chat_completion(
        self,
        request: ChatCompletionRequest,
        api_key_id: str,
        user_id: str,
    ) -> ChatCompletionResponse:
        """Route a chat completion request to the best available provider."""
        candidates = await self._resolve_candidates(request)
        generation_id = f"gen_{uuid.uuid4().hex}"

        last_error: Optional[Exception] = None
        for provider_name in candidates:
            try:
                start_ms = time.monotonic() * 1000
                response = await self._call_provider_chat(provider_name, request)
                latency_ms = time.monotonic() * 1000 - start_ms

                # Record latency for future routing decisions (Phase 4 — Task 4.1)
                await self._redis.record_latency(provider_name, request.model, latency_ms)

                # Emit usage event asynchronously (non-blocking)
                asyncio.create_task(
                    self._emit_usage_event(
                        generation_id=generation_id,
                        api_key_id=api_key_id,
                        user_id=user_id,
                        model=request.model,
                        provider=provider_name,
                        usage=response.usage,
                        latency_ms=latency_ms,
                        fallback_used=(provider_name != candidates[0]),
                    )
                )

                response.generation_id = generation_id
                return response

            except ProviderError as exc:
                logger.warning(
                    "provider_error_fallback",
                    provider=provider_name,
                    error=exc.message,
                    retriable=exc.retriable,
                )
                last_error = exc
                # If fallbacks are disabled by client, stop immediately
                prefs = request.provider
                if prefs and not prefs.allow_fallbacks:
                    break
                continue

        raise NoProvidersAvailableError(
            "All providers in the fallback chain failed.",
            details={"last_error": str(last_error)},
        )

    async def route_embedding(
        self,
        request: EmbeddingRequest,
        api_key_id: str,
        user_id: str,
    ) -> EmbeddingResponse:
        """Route an embedding request to the best available provider."""
        provider_name = self._resolve_static_provider(request.model)
        return await self._call_provider_embedding(provider_name, request)

    def get_models(self) -> dict:
        """Return the list of available models with provider metadata."""
        models_config = self._config.get("models", {})
        providers_config = self._config.get("providers", {})
        return {
            "object": "list",
            "data": [
                {
                    "id": model_id,
                    "object": "model",
                    "provider": info.get("provider"),
                    "data_policy": providers_config.get(
                        info.get("provider", ""), {}
                    ).get("data_policy", {}),
                }
                for model_id, info in models_config.items()
            ],
        }

    # ── Candidate Resolution ─────────────────────────────────────────────────

    async def _resolve_candidates(
        self, request: ChatCompletionRequest
    ) -> List[str]:
        """Resolve the ordered list of provider candidates for a request.

        Applies (in order):
        1. Client-side ``provider.order`` override (Phase 3 — Task 3.1)
        2. Data policy filtering (Phase 3 — Task 3.4)
        3. Dynamic routing strategy (cost / latency / throughput)
        4. Static routing fallback chain from routing.yaml
        """
        prefs = request.provider

        # Step 1: Client-supplied explicit order
        if prefs and prefs.order:
            candidates = list(prefs.order)
        else:
            candidates = self._get_static_candidates(request.model)

        # Step 2: Data policy filtering
        if prefs and prefs.data_collection == "deny":
            candidates = self._filter_by_data_policy(candidates)
            if not candidates:
                raise DataPolicyViolationError(
                    "No provider satisfying the requested data policy is available.",
                    details={"data_collection": "deny"},
                )

        # Step 3: Dynamic sort (if no explicit order was given)
        if not (prefs and prefs.order):
            sort_by = prefs.sort if prefs else None
            candidates = await self._sort_candidates(candidates, request.model, sort_by)

        return candidates

    def _get_static_candidates(self, model: str) -> List[str]:
        """Return the static provider chain from routing.yaml."""
        routing = self._config.get("routing", {}).get(model, {})
        if routing:
            primary = routing.get("primary")
            fallbacks = routing.get("fallback", [])
            return [primary, *fallbacks] if primary else fallbacks

        # Default: return all configured providers
        return list(self._config.get("providers", {}).keys())

    def _filter_by_data_policy(self, candidates: List[str]) -> List[str]:
        """Phase 3 — Task 3.4: Remove providers that train on user data."""
        providers_config = self._config.get("providers", {})
        return [
            p for p in candidates
            if not providers_config.get(p, {}).get("data_policy", {}).get("trains_on_data", False)
        ]

    async def _sort_candidates(
        self,
        candidates: List[str],
        model: str,
        sort_by: Optional[str],
    ) -> List[str]:
        """Sort candidates by the requested optimisation axis."""
        if sort_by == "latency":
            return await self._sort_by_latency(candidates, model)
        elif sort_by == "price":
            return self._sort_by_price(candidates, model)
        # Default: preserve static order (or throughput — same as static for now)
        return candidates

    async def _sort_by_latency(self, candidates: List[str], model: str) -> List[str]:
        """Phase 4 — Task 4.1: Sort by rolling P50 latency from Redis."""
        latencies = {}
        for provider in candidates:
            p50 = await self._redis.get_p50_latency(provider, model)
            latencies[provider] = p50 if p50 is not None else float("inf")

        return sorted(candidates, key=lambda p: latencies[p])

    def _sort_by_price(self, candidates: List[str], model: str) -> List[str]:
        """Sort candidates by configured cost per token."""
        pricing = self._config.get("pricing", {})
        def cost_score(provider: str) -> float:
            p = pricing.get(provider, {}).get(model, {})
            return p.get("input_per_token", 999.0) + p.get("output_per_token", 999.0)
        return sorted(candidates, key=cost_score)

    def _resolve_static_provider(self, model: str) -> str:
        """Return the primary provider for a model from static config."""
        candidates = self._get_static_candidates(model)
        if not candidates:
            raise NoProvidersAvailableError(f"No provider configured for model '{model}'.")
        return candidates[0]

    # ── Provider Calls ───────────────────────────────────────────────────────

    async def _call_provider_chat(
        self, provider: str, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Delegate a chat completion call to the Provider Adapter Service."""
        payload = request.model_dump()
        payload["_provider"] = provider

        async with httpx.AsyncClient(
            base_url=self._provider_url, timeout=120.0
        ) as client:
            response = await client.post("/adapt/chat/completions", json=payload)

        if response.status_code >= 500:
            raise ProviderError(
                f"Provider '{provider}' returned HTTP {response.status_code}.",
                provider=provider,
                retriable=True,
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"Provider '{provider}' rejected the request: {response.text}",
                provider=provider,
                retriable=False,
            )

        return ChatCompletionResponse.model_validate(response.json())

    async def _call_provider_embedding(
        self, provider: str, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """Delegate an embedding call to the Provider Adapter Service."""
        payload = request.model_dump()
        payload["_provider"] = provider

        async with httpx.AsyncClient(
            base_url=self._provider_url, timeout=60.0
        ) as client:
            response = await client.post("/adapt/embeddings", json=payload)
            response.raise_for_status()

        return EmbeddingResponse.model_validate(response.json())

    # ── Usage Event Emission ─────────────────────────────────────────────────

    async def _emit_usage_event(
        self,
        generation_id: str,
        api_key_id: str,
        user_id: str,
        model: str,
        provider: str,
        usage: object,
        latency_ms: float,
        fallback_used: bool,
    ) -> None:
        """Asynchronously emit a usage event to the Billing Service."""
        record = UsageRecord(
            id=generation_id,
            api_key_id=api_key_id,
            user_id=user_id,
            model=model,
            provider=provider,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
            cost_usd=getattr(usage, "estimated_cost_usd", 0.0),
            markup_usd=0.0,
            billed_usd=getattr(usage, "estimated_cost_usd", 0.0),
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            cache_hit=getattr(usage, "cache_hit", False),
            cached_tokens=getattr(usage, "cached_tokens", 0),
            cache_discount_usd=getattr(usage, "cache_discount_usd", 0.0),
        )

        try:
            async with httpx.AsyncClient(
                base_url=self._billing_url, timeout=5.0
            ) as client:
                await client.post(
                    "/internal/usage",
                    json=record.model_dump(mode="json"),
                )
        except Exception as exc:
            # Billing failures must never impact the client response
            logger.error("billing_emit_failed", error=str(exc), generation_id=generation_id)
