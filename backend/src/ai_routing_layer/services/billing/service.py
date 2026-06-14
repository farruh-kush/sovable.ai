from __future__ import annotations

from collections import defaultdict

from ai_routing_layer.models import UsageInfo, UsageRecord


class PricingCatalog:
    def __init__(self) -> None:
        self._pricing: dict[tuple[str, str], tuple[float, float]] = {
            ("openai", "gpt-4o-mini"): (0.00000015, 0.00000060),
            ("openai", "gpt-4"): (0.00003, 0.00006),
            ("anthropic", "claude-3-5-sonnet-latest"): (0.000003, 0.000015),
            ("anthropic", "gpt-4o-mini"): (0.000003, 0.000015),
        }
        self._default_markup = 0.15

    def calculate_cost(self, provider: str, model: str, usage: UsageInfo) -> float:
        prompt_rate, completion_rate = self._pricing.get(
            (provider, model),
            (0.000001, 0.000002),
        )
        base_cost = usage.prompt_tokens * prompt_rate + usage.completion_tokens * completion_rate
        return round(base_cost * (1 + self._default_markup), 8)


class UsageStore:
    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    def add(self, record: UsageRecord) -> None:
        self._records.append(record)

    def list_records(self) -> list[UsageRecord]:
        return list(self._records)

    def total_cost_by_api_key(self, api_key_id: str) -> float:
        return round(
            sum(record.cost_usd for record in self._records if record.api_key_id == api_key_id),
            8,
        )

    def aggregate_by_user(self) -> dict[str, dict[str, float]]:
        totals: dict[str, dict[str, float]] = defaultdict(lambda: {"cost_usd": 0.0, "requests": 0})
        for record in self._records:
            totals[record.user_id]["cost_usd"] += record.cost_usd
            totals[record.user_id]["requests"] += 1
        return totals


class BillingService:
    def __init__(self, catalog: PricingCatalog, usage_store: UsageStore) -> None:
        self.catalog = catalog
        self.usage_store = usage_store

    def enrich_usage(self, provider: str, model: str, usage: UsageInfo) -> UsageInfo:
        usage.estimated_cost_usd = self.catalog.calculate_cost(provider, model, usage)
        return usage

    def enforce_quota(self, api_key_id: str, daily_quota_usd: float) -> None:
        spent = self.usage_store.total_cost_by_api_key(api_key_id)
        if spent >= daily_quota_usd:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Daily quota exceeded",
            )

    def record(self, record: UsageRecord) -> None:
        self.usage_store.add(record)
