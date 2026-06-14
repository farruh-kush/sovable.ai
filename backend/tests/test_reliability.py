import pytest

from ai_routing_layer.auth.service import Principal
from ai_routing_layer.billing.service import BillingService, PricingCatalog, UsageStore
from ai_routing_layer.models import ChatCompletionRequest, ChatMessage
from ai_routing_layer.observability.metrics import MetricsRegistry
from ai_routing_layer.providers.base import ProviderError, ProviderErrorPayload
from ai_routing_layer.router.engine import RoutingEngine
from ai_routing_layer.service import RoutingService


class FailingProvider:
    name = "broken"

    class _Health:
        error_count = 0
        last_latency_ms = 50.0

        @staticmethod
        def available() -> bool:
            return True

    health = _Health()

    async def chat(self, request):
        raise ProviderError(
            ProviderErrorPayload(code="broken", message="upstream failure", provider="broken", retriable=True)
        )

    async def chat_stream(self, request):
        yield None

    async def embeddings(self, request):
        raise NotImplementedError


class BackupProvider(FailingProvider):
    name = "backup"

    async def chat(self, request):
        from ai_routing_layer.models import ChatChoice, ChatCompletionResponse, UsageInfo
        import time

        usage = UsageInfo(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        return ChatCompletionResponse(
            id="resp_1",
            created=int(time.time()),
            model=request.model,
            provider="backup",
            choices=[ChatChoice(index=0, message={"role": "assistant", "content": "ok"}, finish_reason="stop")],
            usage=usage,
        )


class Registry:
    def __init__(self):
        self.providers = {"broken": FailingProvider(), "backup": BackupProvider()}

    def get(self, name):
        return self.providers[name]

    def all(self):
        return list(self.providers.values())


@pytest.mark.asyncio
async def test_fallback_used_when_primary_fails(tmp_path) -> None:
    config_path = tmp_path / "routing.yaml"
    config_path.write_text(
        "routing:\n  gpt-4o-mini:\n    primary: broken\n    fallback:\n      - backup\n",
        encoding="utf-8",
    )
    router = RoutingEngine(Registry(), config_path)
    service = RoutingService(router, BillingService(PricingCatalog(), UsageStore()), MetricsRegistry())
    principal = Principal(
        api_key_id="key_1",
        user_id="user_1",
        requests_per_minute=10,
        requests_per_day=100,
        daily_quota_usd=100,
    )
    response = await service.create_chat_completion(
        ChatCompletionRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hi")]),
        principal,
    )
    assert response.provider == "backup"
