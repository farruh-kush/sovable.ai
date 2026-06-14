from __future__ import annotations


from prometheus_client import Counter, Histogram


class MetricsRegistry:
    """Singleton-style Prometheus metrics registry.

    Prometheus raises an error if the same metric name is registered twice,
    so we guard initialisation with a class-level flag and store the metric
    objects as class attributes with explicit type annotations to satisfy mypy.
    """

    _initialized: bool = False
    request_latency_seconds: Histogram  # type: ignore[assignment]
    request_errors_total: Counter  # type: ignore[assignment]
    provider_requests_total: Counter  # type: ignore[assignment]

    def __init__(self) -> None:
        if MetricsRegistry._initialized:
            # Re-use already-registered metrics on subsequent instantiations.
            return
        MetricsRegistry.request_latency_seconds = Histogram(
            "ai_router_request_latency_seconds",
            "Request latency by endpoint and provider",
            ["endpoint", "provider"],
        )
        MetricsRegistry.request_errors_total = Counter(
            "ai_router_request_errors_total",
            "Error count by endpoint and provider",
            ["endpoint", "provider"],
        )
        MetricsRegistry.provider_requests_total = Counter(
            "ai_router_provider_requests_total",
            "Provider request count",
            ["provider", "status"],
        )
        MetricsRegistry._initialized = True

    # ── Convenience accessors ─────────────────────────────────────────────────

    def observe_latency(self, endpoint: str, provider: str, latency: float) -> None:
        MetricsRegistry.request_latency_seconds.labels(
            endpoint=endpoint, provider=provider
        ).observe(latency)

    def inc_errors(self, endpoint: str, provider: str) -> None:
        MetricsRegistry.request_errors_total.labels(endpoint=endpoint, provider=provider).inc()

    def inc_provider_requests(self, provider: str, status: str) -> None:
        MetricsRegistry.provider_requests_total.labels(provider=provider, status=status).inc()
