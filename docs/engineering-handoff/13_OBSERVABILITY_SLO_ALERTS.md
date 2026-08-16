# Solvable Observability, SLOs, and Alerting Specification

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Observability goals

Solvable must explain whether a request was accepted, which policy allowed it, which route was selected, whether masking occurred, how providers behaved, what the customer was charged, and whether the platform met its service objectives. Observability data is itself sensitive and must follow the masking, retention, and tenant-isolation policies.

The platform uses OpenTelemetry instrumentation, Prometheus-compatible metrics, Grafana dashboards, Loki or an equivalent structured log store, and trace storage appropriate to deployment. The stack is replaceable as long as semantic fields and retention behavior remain stable.

## 2. Correlation model

Every request carries `request_id`, `trace_id`, `span_id`, `organization_id`, `project_id`, `service`, `environment`, and `route_decision_id` where available. Customer-visible support evidence uses request IDs; operators use traces and logs. Raw prompt and response content are absent by default.

## 3. Metrics taxonomy

### Gateway metrics

- `solvable_gateway_requests_total{route,method,status_class}`
- `solvable_gateway_request_duration_seconds{route,status_class}`
- `solvable_gateway_inflight_requests{route}`
- `solvable_gateway_request_body_bytes`
- `solvable_gateway_stream_duration_seconds`
- `solvable_gateway_rate_limit_decisions_total{scope,decision}`

### Router metrics

- `solvable_router_decisions_total{policy,decision}`
- `solvable_router_candidate_exclusions_total{reason}`
- `solvable_router_selected_total{provider,model}`
- `solvable_router_fallback_total{from_provider,to_provider}`
- `solvable_router_retry_total{error_class}`
- `solvable_router_circuit_state{provider,endpoint}`
- `solvable_router_decision_duration_seconds`

### Provider metrics

- `solvable_provider_attempts_total{provider,model,status_class}`
- `solvable_provider_latency_seconds{provider,model}`
- `solvable_provider_timeout_total{provider,model}`
- `solvable_provider_rate_limit_total{provider,model}`
- `solvable_provider_invalid_response_total{provider,model}`
- `solvable_provider_health_score{provider,endpoint}`

### Billing and privacy metrics

- `solvable_usage_tokens_total{model,direction}`
- `solvable_usage_cost_minor_total{organization,project,model}` with controlled cardinality
- `solvable_budget_decisions_total{scope,decision}`
- `solvable_ledger_events_total{status}`
- `solvable_privacy_decisions_total{action,class}`
- `solvable_privacy_detection_errors_total{detector}`

Do not put request ID, prompt, API key, email, arbitrary user metadata, or full error messages into metric labels.

## 4. Logs

All services emit JSON structured logs with timestamp, level, service, environment, request ID, trace ID, organization/project identifiers where safe, operation, status, latency, error class, and schema version. Logs are redacted before storage. Provider request/response bodies and credentials are never logged by default. Access to restricted logs is role-gated and audited.

Standard log levels are `debug` for local development, `info` for lifecycle and business events, `warn` for degraded behavior, and `error` for failed operations. Repeated provider failures should be represented by counters and a single useful error event, not a log storm.

## 5. Traces

Trace spans cover gateway authentication, policy evaluation, masking, route selection, cache lookup, provider attempt, response normalization, usage calculation, billing publication, and stream lifecycle. Each span includes safe attributes for model, provider, policy version, cache status, retry number, and error class. Prompt content is excluded unless a tightly controlled development-only feature is enabled.

## 6. SLOs

Initial service objectives are:

| SLO | Target | Window | Notes |
|---|---:|---:|---|
| Gateway availability | 99.5% | 30 days | Excludes planned maintenance with notice. |
| Gateway non-streaming overhead p99 | <200 ms | 30 days | Measured before upstream provider latency. |
| Chat request success | 99.0% | 30 days | Excludes caller validation and policy blocks. |
| Streaming time-to-first-token overhead p95 | <500 ms | 30 days | Provider latency separated. |
| Usage ledger completeness | 99.9% | 24 hours | Accepted requests have usage state. |
| Billing event timeliness | 99.5% within 5 min | 30 days | Measured to ledger read model. |
| Provider health freshness | 99% within 60 s | 30 days | Admin health data. |
| Control-plane read availability | 99.5% | 30 days | Console API. |

Error budgets are calculated by SLO window. A team should reduce risky releases when the error budget is exhausted and prioritize reliability work.

## 7. Dashboards

### Platform overview

Shows availability, request rate, error rate by class, p50/p95/p99 gateway latency, inflight requests, saturation, active alerts, and deploy markers.

### Provider health

Shows provider/model request volume, success rate, timeout/rate-limit/5xx rates, p50/p95/p99 latency, circuit state, fallback rate, current price version, and last credential health check. Health is segmented by endpoint and region.

### Router effectiveness

Shows candidate exclusion reasons, selected provider/model mix, cost and latency scores, fallback frequency, retry rate, cache hit rate, and policy version changes. A route dashboard must help distinguish policy choice from provider degradation.

### Billing and cost

Shows provider cost, platform charge, free-quota consumption, spend by organization/project/model/provider, estimated-versus-finalized usage, budget threshold events, adjustment volume, and reconciliation lag. Customer dashboards enforce tenant filters.

### Security and privacy

Shows authentication failures, key revocations, privilege changes, unusual request spikes, privacy blocks, credential detections, app permission denials, and break-glass events.

## 8. Alert rules

| Alert | Severity | Trigger | First action |
|---|---|---|---|
| Gateway availability burn | Critical | SLO burn rate exceeds paging threshold. | Page on-call; check ingress, gateway, dependencies. |
| Gateway p99 overhead | Warning/Critical | p99 exceeds 200 ms for sustained window. | Inspect saturation, auth, router, cache, DB. |
| Provider outage | Critical | Provider error/timeout rate and health threshold breached. | Disable or route away; validate fallback. |
| Provider rate limiting | Warning | 429 rate above threshold. | Check quotas, backoff, alternate candidates. |
| Circuit open | Warning | Circuit open for approved provider/model. | Review health and route policy. |
| Billing lag | Critical | Accepted requests missing ledger state beyond SLA. | Inspect event bus, billing consumer, idempotency. |
| Budget anomaly | High | Spend velocity or forecast exceeds policy. | Freeze affected scope and investigate. |
| Privacy detector failure | High | Detector errors or policy fail-open attempt. | Fail closed for high-security policy. |
| Auth abuse | High | Credential stuffing, key misuse, privilege escalation pattern. | Revoke/lock, inspect audit, rotate if needed. |
| Export failure | Warning | Repeated export job failure. | Check object storage and worker capacity. |
| Backup failure | Critical | Backup or restore verification fails. | Escalate to data owner; suspend risky changes. |

Alerts include owner, runbook URL, query, severity, deduplication key, remediation, and evidence links.

## 9. Health checks

Liveness verifies process health. Readiness verifies required local dependencies and configuration. Provider health probes use bounded, low-cost, policy-approved calls or metadata checks. A provider health check must not consume unlimited model quota or leak customer content.

## 10. Incident evidence

For each incident, preserve alert, timeline, deploy/version, dashboards, representative request IDs, route decisions, provider attempts, logs, traces, policy versions, billing state, mitigation, and customer impact. Redact credentials and sensitive content before sharing.

## 11. Retention and access

Metrics retain enough history for SLO windows and capacity trends. Logs and traces have environment-specific retention. Tenant-scoped analytics and platform operations are separated. Break-glass access is time-limited and audited.

## 12. Acceptance criteria

An operator can trace a request ID from gateway through route selection, provider attempt, response normalization, and billing event without reading raw prompt content. A provider outage produces an alert and route behavior changes according to policy. A budget anomaly is visible before the hard stop. SLO dashboards calculate from stable queries and survive a service restart.

## References

[1]: https://opentelemetry.io/docs/concepts/semantic-conventions/ "OpenTelemetry Semantic Conventions"
[2]: https://opentelemetry.io/docs/specs/semconv/gen-ai/ "OpenTelemetry Generative AI Semantic Conventions"
