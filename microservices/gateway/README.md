# Solvable AI Gateway

The gateway is the public, OpenAI-compatible HTTP boundary for the Solvable AI Routing Layer. It owns request validation, API-key validation through Auth, rate limiting and monthly budget checks through Redis, forwarding to Router and Billing over HTTP, SSE response proxying, and redacted privacy previews. It does not read a peer service database and does not contain provider credentials.

## Local validation

From the repository root, install the shared contract package and gateway development dependencies into the project environment, then run the service-local checks:

```bash
python -m pip install -e backend/shared -e 'microservices/gateway[dev]'
PYTHONPATH=backend/shared/src:microservices/gateway/src python -m pytest microservices/gateway/tests -q
PYTHONPATH=backend/shared/src:microservices/gateway/src python -m compileall -q backend/shared/src/ai_routing_shared microservices/gateway/src
```

The gateway test suite uses `respx` to mock Auth and Router HTTP contracts. It covers API-key extraction, malformed request validation, model allowlists, rate and budget exhaustion, Router 4xx/5xx and timeout mapping, SSE forwarding, activation-link forwarding, privacy preview forwarding, request IDs, cache-key determinism, and secret redaction.

## Debugging by request ID

Every request receives an `X-Request-Id` response header. A caller may supply a trusted correlation value with the same request header; otherwise the gateway generates a UUID. The value is bound to structured-log context by shared middleware and is forwarded to peer HTTP calls. Use the request ID to correlate gateway, Auth, Router, Provider, and Billing events without searching on request content or credentials.

The gateway emits JSON logs through `structlog`. Useful fields include `service`, `event`, `timestamp`, `request_id`, `api_key_id` when a principal has been validated, `peer_service` for dependency calls, `provider` when emitted by downstream services, `status`, `error_code`, `limit`, `window_seconds`, and `generation_id` where available. Request bodies, raw API keys, cookies, authorization values, and upstream response bodies must not be logged. A log event such as `auth_service_error` contains only an HTTP status; `peer_timeout` and `peer_unreachable` identify the dependency but not its body.

For a local dependency-free smoke test, inject a fake Redis state in the test harness or run Redis/Valkey with the service configuration, then call `/health`. A healthy response has `{"status":"healthy","service":"gateway"}` and `dependencies.redis` equal to `ok`; a Redis failure is reported as `degraded` without leaking the connection error to the client. A 401 from Auth means the key is missing, conflicting, invalid, or expired. A 429 means a rate or monthly budget policy blocked the request. A 502/504 indicates a peer failure or timeout, not a provider secret or stack trace.

## Public response behavior

Malformed public payloads return HTTP 422 with `error.code=invalid_request`. Domain policy failures use the shared envelope, including `authentication_error`, `model_not_allowed`, `rate_limit_exceeded`, and `monthly_budget_exceeded`. Peer 4xx responses are returned as sanitized `upstream_rejected` errors while peer 5xx responses become `upstream_service_error`; peer timeouts become `upstream_timeout` with HTTP 504. Streaming failures that occur after SSE headers have been sent are represented as an SSE error event followed by `data: [DONE]` because the HTTP status can no longer be changed.

The gateway’s activation routes preserve the existing public paths `/auth/email/activation/start` and `/auth/email/activation/complete`, forward the request to Auth, and return only Auth’s JSON response. OAuth redirects are passed through without following them server-side. The privacy preview route forwards the authenticated principal identity to Router and returns Router’s masked preview; the raw API key is never sent to Router.

## Rollback considerations

Deploy the gateway as an independently versioned image and roll back only the gateway deployment when a gateway regression is detected. Before rollout, run the service-local tests and the container build. During rollout, monitor 4xx/5xx rates, `upstream_timeout`, `peer_unreachable`, `rate_limit_exceeded`, Redis health, and latency by request ID. Keep the previous image available until the new image has passed readiness and a representative non-streaming and streaming request has succeeded.

The atomic Redis rate-limit script is backward-compatible with the existing `rl:<api_key_id>:minute` and `rl:<api_key_id>:day` key namespaces. Do not flush Redis during rollback: the sorted-set windows and spend cache are shared operational state. If the new gateway image must be reverted, restore the previous deployment image and retain the current Redis state. If the error-envelope change causes a client compatibility issue, roll back the gateway image first; do not bypass Auth or Router by connecting directly to their databases. Changes to the shared exception or request models should be rolled back together with any service images built from the same shared snapshot.
