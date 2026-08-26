from __future__ import annotations

from pathlib import Path

import pytest
from router.core.catalog import CatalogError, CatalogManager
from router.engine.policy import (
    NoRoute,
    PolicyEvaluator,
    ProviderHealthSignal,
    RouteContext,
)

ROOT = Path(__file__).resolve().parents[3]
CATALOG = CatalogManager(ROOT / "ai" / "config" / "routing.yaml")


def evaluator() -> PolicyEvaluator:
    return PolicyEvaluator(CATALOG.snapshot())


def test_catalog_contains_western_chinese_and_open_source_families() -> None:
    catalog = CATALOG.snapshot()
    assert {"openai", "anthropic", "google", "mistral"} <= set(catalog.providers)
    assert {"alibaba", "moonshot", "zhipu", "deepseek"} <= set(catalog.providers)
    assert "open_source" in catalog.providers
    assert catalog.models["qwen-plus"].provider == "alibaba"
    assert catalog.models["text-embedding-v4"].kind == "embedding"


def test_policy_precedence_applies_region_compliance_before_strategy() -> None:
    policy = evaluator()
    decision = policy.decide(
        "gpt-4o",
        RouteContext(
            correlation_id="corr-1",
            tenant_id="tenant-a",
            region="eu",
            compliance=frozenset({"gdpr", "zero_data_retention"}),
        ),
    )
    assert decision.selected_provider == "openai"
    assert "anthropic" in decision.rejected
    assert "openai" not in decision.rejected
    assert decision.correlation_id == "corr-1"
    assert decision.decision_id.startswith("route_")


def test_health_and_deny_list_exclude_provider_deterministically() -> None:
    catalog = CATALOG.snapshot()
    policy = PolicyEvaluator(
        catalog, {"openai": ProviderHealthSignal(circuit_open=True)}
    )
    decision = policy.decide("gpt-4o-mini", RouteContext(correlation_id="corr-2"))
    assert decision.selected_provider == "mistral"
    assert "circuit_open" in decision.rejected["openai"]


def test_cost_alias_selects_concrete_model_and_is_stable() -> None:
    policy = evaluator()
    context = RouteContext(correlation_id="corr-3", tenant_id="tenant-a")
    first = policy.decide("cheapest", context)
    second = policy.decide("cheapest", context)
    assert first.as_dict() == second.as_dict()
    assert first.selected_model in {
        "gpt-4o-mini",
        "gemini-1.5-flash",
        "mistral-small-latest",
        "deepseek-chat",
    }
    assert first.selected_provider in first.candidates


def test_streaming_and_compliance_constraints_are_hard_filters() -> None:
    policy = evaluator()
    with pytest.raises(NoRoute):
        policy.decide(
            "gpt-4o",
            RouteContext(
                correlation_id="corr-4",
                region="cn",
                streaming=True,
                compliance=frozenset({"zero_data_retention"}),
            ),
        )


def test_catalog_redaction_exposes_env_names_not_secret_values() -> None:
    data = CATALOG.redacted_snapshot()
    assert "api_key_env" not in data["providers"]["openai"]
    serialized = repr(data).lower()
    assert "sk-" not in serialized
    assert "authorization" not in serialized


def test_invalid_reload_retains_last_valid_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "routing.yaml"
    path.write_text(
        (ROOT / "ai" / "config" / "routing.yaml").read_text(), encoding="utf-8"
    )
    manager = CatalogManager(path)
    original = manager.checksum
    path.write_text("providers: {}\n", encoding="utf-8")
    assert manager.reload_if_changed() is False
    assert manager.checksum == original
    assert manager.snapshot().catalog_version == "2026.08.26"


def test_unknown_catalog_provider_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "routing.yaml"
    path.write_text(
        "schema_version: '1'\ncatalog_version: '1'\npolicy_version: '1'\nproviders: {}\nmodels: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError):
        CatalogManager(path)
