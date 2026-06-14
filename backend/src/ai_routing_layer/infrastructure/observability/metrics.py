from prometheus_client import Counter, Histogram


class MetricsRegistry:
    _initialized = False

    def __init__(self) -> None:
        if self.__class__._initialized:
            self.request_latency_seconds = self.__class__.request_latency_seconds
            self.request_errors_total = self.__class__.request_errors_total
            self.provider_requests_total = self.__class__.provider_requests_total
            return
        self.__class__.request_latency_seconds = Histogram(
            "ai_router_request_latency_seconds",
            "Request latency by endpoint and provider",
            ["endpoint", "provider"],
        )
        self.__class__.request_errors_total = Counter(
            "ai_router_request_errors_total",
            "Error count by endpoint and provider",
            ["endpoint", "provider"],
        )
        self.__class__.provider_requests_total = Counter(
            "ai_router_provider_requests_total",
            "Provider request count",
            ["provider", "status"],
        )
        self.request_latency_seconds = self.__class__.request_latency_seconds
        self.request_errors_total = self.__class__.request_errors_total
        self.provider_requests_total = self.__class__.provider_requests_total
        self.__class__._initialized = True
