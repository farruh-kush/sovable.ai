from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    host: str = "127.0.0.1"
    port: int = 0
    internal_secret: str = "local-dev-internal-secret"
    auth_url: str = "http://127.0.0.1:8101"
    router_url: str = "http://127.0.0.1:8102"
    provider_url: str = "http://127.0.0.1:8103"
    billing_url: str = "http://127.0.0.1:8104"
    gateway_api_key: str = "sk-local-demo"
    monthly_budget_usd: float = 100.0


def settings(service_name: str, default_port: int) -> Settings:
    return Settings(
        service_name=service_name,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", str(default_port))),
        internal_secret=os.getenv("INTERNAL_SECRET", "local-dev-internal-secret"),
        auth_url=os.getenv("AUTH_URL", "http://127.0.0.1:8101"),
        router_url=os.getenv("ROUTER_URL", "http://127.0.0.1:8102"),
        provider_url=os.getenv("PROVIDER_URL", "http://127.0.0.1:8103"),
        billing_url=os.getenv("BILLING_URL", "http://127.0.0.1:8104"),
        gateway_api_key=os.getenv("GATEWAY_API_KEY", "sk-local-demo"),
        monthly_budget_usd=float(os.getenv("MONTHLY_BUDGET_USD", "100.0")),
    )
