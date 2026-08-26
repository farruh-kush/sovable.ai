# Provider Adapter Service

The Provider Adapter Service is an isolated HTTP boundary between Gateway/Router and upstream model providers. It owns provider-specific authentication, request translation, response normalization, streaming parsing, embeddings, capability metadata, retry budgets, circuit-breaker signals, connection pooling, and provider error classification. It does not access another service database and it does not persist request prompts.

## Versioned HTTP contract

The canonical route family is `/v1/adapt`. The legacy `/adapt` route family remains available for backward compatibility with existing Gateway deployments.

| Operation | Method | Versioned route | Required selector | Result |
|---|---|---|---|---|
| Chat completion | `POST` | `/v1/adapt/chat/completions` | `_provider` | Normalized `ChatCompletionResponse` or SSE |
| Embeddings | `POST` | `/v1/adapt/embeddings` | `_provider` | Normalized `EmbeddingResponse` |
| Health | `GET` | `/v1/adapt/health` | None | Provider health and circuit signals |
| Capabilities | `GET` | `/v1/adapt/capabilities` | None | Safe capability metadata; no upstream probing by default |

For streaming requests, set `stream: true`. Each event is `data: <normalized ChatCompletionChunk JSON>`, followed by `data: [DONE]`. Provider request IDs and correlation IDs are represented in error metadata rather than raw upstream bodies.

## Adapter onboarding

A new provider should subclass `BaseProviderAdapter` or `OpenAICompatibleAdapter` when the upstream API is OpenAI-shaped. Implement the three typed methods `_chat_impl`, `_chat_stream_impl`, and `_embedding_impl`, add a capability set, and normalize provider-specific finish reasons and usage fields. Register the adapter in `ProviderRegistry`, add its environment-backed secret to `ProviderSettings`, and add its host to an explicit HTTPS allowlist. The adapter must use the shared pooled client and must never log or return credentials.

A provider adapter must have deterministic behavior when no secret is available. Local tests may use `PROVIDER_MOCK_MODE=true`; production deployments should set `PROVIDER_MOCK_MODE=false` so an unconfigured provider is classified as an authentication/configuration failure rather than silently calling a mock.

## Supported providers and capabilities

| Provider selector | Adapter | Chat | Streaming | Embeddings | Tools/JSON | Authentication source |
|---|---|---:|---:|---:|---:|---|
| `openai` | `OpenAIAdapter` | Yes | Yes | Yes | Pass-through | `OPENAI_API_KEY` |
| `anthropic` | `AnthropicAdapter` | Yes | Yes | No native adapter | Provider-specific tools can be added | `ANTHROPIC_API_KEY` |
| `google` | `GoogleAdapter` | Yes | Yes | Yes | Provider-specific extensions can be added | `GOOGLE_API_KEY` |
| `mistral` | `MistralAdapter` | Yes | Yes | Yes | Compatible pass-through | `MISTRAL_API_KEY` |
| `alibaba` / `qwen` | `AlibabaQwenAdapter` | Yes | Yes | Yes | Compatible pass-through | `DASHSCOPE_API_KEY` or `QWEN_API_KEY` |

Capability discovery is local and safe by default. It reports adapter-declared support and configured state without sending synthetic traffic to an upstream provider. Health checks report `ready`, `degraded`, `circuit_open`, or `unconfigured` and contain only latency and counters.

## Environment variables

Secrets are injected from Kubernetes Secrets into the process environment. They are not read from source files, request bodies, databases, or arbitrary URLs.

| Variable | Default | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | unset | OpenAI credential |
| `OPENAI_BASE_URL` | OpenAI API URL | Explicitly allowlisted HTTPS OpenAI or trusted proxy endpoint |
| `ANTHROPIC_API_KEY` | unset | Anthropic credential |
| `GOOGLE_API_KEY` | unset | Gemini credential |
| `MISTRAL_API_KEY` | unset | Mistral credential |
| `DASHSCOPE_API_KEY` | unset | Alibaba Model Studio credential |
| `QWEN_API_KEY` | unset | Compatibility alias for Alibaba/Qwen credential |
| `PROVIDER_MOCK_MODE` | `true` | Deterministic local mock mode; disable in production |
| `PROVIDER_RETRY_MAX_ATTEMPTS` | `3` | Total request attempts, bounded to 1–5 |
| `PROVIDER_MAX_CONCURRENCY` | `32` | Per-adapter in-flight request limit |
| `DEFAULT_TIMEOUT_SECONDS` | `30` | Bounded request timeout |
| `PROVIDER_CIRCUIT_FAILURE_THRESHOLD` | `3` | Consecutive failures before opening the circuit |
| `PROVIDER_CIRCUIT_OPEN_SECONDS` | `30` | Circuit-open duration |
| `PROVIDER_ALLOWLIST` | registered providers | Provider selectors permitted by policy |

## Failure matrix

| Upstream condition | Classification | Retryable | Adapter behavior | Router signal |
|---|---|---:|---|---|
| `401` or `403` | `authentication` | No | Redacted provider error | Do not retry; select another authorized provider |
| `429` | `rate_limit` | Yes | Honor bounded `Retry-After`, then retry within budget | Provider rate-limit signal |
| `408`, `409`, `425` | `server_error` | Yes | Exponential backoff with jitter | Temporary upstream failure |
| `5xx` | `server_error` | Yes | Retry, record failure, open circuit at threshold | Provider unavailable |
| HTTP timeout | `timeout` | Yes | Retry within deadline and concurrency budget | Provider timeout |
| Network error | `network` | Yes | Retry within budget | Provider unavailable |
| Invalid request | `invalid_request` | No | Return normalized validation/provider error | Do not retry |
| Invalid JSON or unexpected shape | `malformed_response` | No | Fail closed without returning raw body | Upstream invalid response |
| Circuit open | `circuit_open` | No at adapter layer | Fail fast | Skip provider until health recovers |
| Cancelled request | `cancelled` | No | Propagate cancellation and release semaphore | No retry |

## Debugging signals

Structured logs contain event names, provider selector, model name, stream mode, and correlation ID. They intentionally exclude API keys, authorization headers, raw prompt content, raw upstream response bodies, and activation material. Useful events include `providers_registered`, `provider_chat_start`, `provider_embedding_start`, `provider_request_cancelled`, and `provider_circuit_open`.

The health endpoint exposes `last_latency_ms`, `consecutive_failures`, `circuit_open`, and the high-level `signal`. Correlate Gateway and Router logs using `X-Request-Id` or `X-Correlation-Id`. Provider-specific request IDs are carried only in structured error details when the upstream supplies them.

## Deployment dependencies and rollback

The service requires Python 3.11+, FastAPI, httpx, Pydantic v2, structlog, and the installed `ai-routing-shared` package. Kubernetes deployment must provide an egress policy allowing only the provider hosts declared in adapter allowlists and must mount credentials as Secrets exposed through environment variables. No provider database is required.

Rollback is isolated: deploy the previous provider-service image while keeping Gateway and Router on the same versioned contract, or disable a provider selector through `PROVIDER_ALLOWLIST`. The legacy `/adapt` routes remain available during a rolling deployment. If a provider misbehaves, remove its selector from the allowlist or allow its circuit to open; do not delete shared databases or alter Gateway request schemas.

## Testing

Run service-local tests from the repository root:

```bash
PYTHONPATH=shared/src:services/provider/src python3 -m pytest services/provider/tests -q
```

The suite covers normalized request/response behavior, usage and cost mapping, capability flags, timeout and retry classification, circuit budgets, cancellation, pooled client reuse, deterministic Alibaba/Qwen success/quota/malformed/timeout/outage fixtures, SSE parsing, embeddings, provider allowlisting, secret redaction, and SSRF prevention.
