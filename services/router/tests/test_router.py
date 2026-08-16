from pathlib import Path
import pytest
from ai_routing_shared.models import ChatCompletionRequest
from ai_routing_shared.models import ChatMessage
from ai_routing_shared.models import ProviderPreferences
from router.engine.routing_engine import RoutingEngine

class FakeRedis:
    async def get_p50_latency(self, provider: str, model: str):
        return {"openai": 500.0, "mistral": 100.0}.get(provider)

def engine() -> RoutingEngine:
    return RoutingEngine(
        Path("config/routing.yaml"),
        "http://provider:8003",
        "http://billing:8004",
        FakeRedis(),
    )

def test_static_chain_for_gpt_mini() -> None:
    assert engine()._get_static_candidates("gpt-4o-mini") == ["openai", "mistral"]

@pytest.mark.asyncio
async def test_latency_sort_prefers_measured_provider() -> None:
    result = await engine()._sort_by_latency(
        ["openai", "mistral"], "gpt-4o-mini"
    )
    assert result == ["mistral", "openai"]

@pytest.mark.asyncio
async def test_deny_data_collection_keeps_zdr_providers() -> None:
    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="email test@example.com")],
        provider=ProviderPreferences(data_collection="deny"),
    )
    candidates = await engine()._resolve_candidates(request)
    assert candidates == ["openai", "mistral"]

@pytest.mark.asyncio
async def test_masking_restores_original_text() -> None:
    from ai_routing_shared.privacy import mask_chat_messages
    messages = [ChatMessage(role="user", content="Reach test@example.com")]
    masked, session = mask_chat_messages(messages)
    assert "test@example.com" not in masked[0].content
    assert session.restore_text(masked[0].content) == "Reach test@example.com"
