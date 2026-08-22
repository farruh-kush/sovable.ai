# Solvable Service Catalog

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Service catalog principles

Every service owns one domain and exposes a versioned contract. Service code must not reach into another service’s private database. Shared code is limited to stable cross-service types, error classes, middleware, and serialization helpers. Domain decisions remain in the owning service.

## 2. Current and target services

| Service/module | Repository location | Responsibility | State owner | Current status |
|---|---|---|---|---|
| Gateway | `microservices/gateway` | Public API, authentication dependency, request lifecycle, streaming, normalized errors, request IDs, cache/policy coordination. | Redis for ephemeral cache/limits; no domain database. | Current core service. |
| Auth / Identity | `microservices/auth` | Users, organizations, workspaces, projects, members, roles, sessions, API keys, service identities, invitations, MFA metadata. | `auth_db`. | Current service; organization expansion required. |
| Router / Aggregator | `microservices/router` | Candidate discovery, policy filtering, route scoring, fallback, retries, circuit breakers, route explanations, health state. | Versioned policy catalog; Redis health cache; durable route-decision events. | Current core service; target policy engine expansion required. |
| Provider | `microservices/provider` | Provider adapter registry, upstream calls, response normalization, usage extraction, provider errors, capability checks. | Provider/model catalog and secret references. | Current core service. |
| Billing / Usage | `microservices/billing` | Usage ledger, pricing, provider cost, markup, credits, budgets, invoices, adjustments, reconciliation. | `billing_db`. | Current service; append-only ledger expansion required. |
| Privacy / Data Protection | Target module or service | Sensitive-data detection, masking, tokenization, blocking, restoration, retention evidence, provider eligibility. | Policy catalog plus request-scoped protected mapping. | Target increment; start as bounded module before extraction. |
| Catalog / Policy | Target control-plane module | Providers, models, capabilities, price versions, route policies, masking policies, retention policies. | Control-plane database or a dedicated catalog schema. | Target increment; avoid duplicating routing YAML indefinitely. |
| Data Platform | Target event and pipeline layer | Event ingestion, schema registry, sanitized analytics, warehouse exports, lineage, quality checks. | Event bus, object storage, warehouse. | Target increment. |
| Marketplace | Target service | Agent/app catalog, publisher verification, manifests, versions, approvals, installations, reviews, takedowns. | Marketplace database and signed artifact storage. | Target increment. |
| Agent Runtime | Target isolated runtime | Execute approved agents, workflows, tools, and connectors with declared permissions and resource limits. | Ephemeral run state plus event/audit records. | Target increment. |
| Web Console | `frontend/dashboard` and static site | Public website, authenticated User Panel, Admin Panel, Playground, docs, usage, billing, marketplace. | Browser state plus API services. | Current UI baseline; authenticated expansion required. |
| Shared library | `backend/shared/src/ai_routing_shared` | Shared types, exceptions, serialization, middleware, logging helpers, configuration primitives. | None. | Current shared package. |
| Operations | `infrastructure/observability/` plus platform stack | OpenTelemetry, Prometheus, Grafana, Loki, alert rules, dashboards, synthetic checks, incident metadata. | Metrics/logs/traces backends. | Current assets; production hardening required. |

## 3. Service contracts and dependencies

| Caller | Callee | Contract | Synchronous? | Failure behavior |
|---|---|---|---|---|
| Client | Gateway | Public `/v1` API | Yes/stream | Stable normalized error; request ID returned. |
| Gateway | Auth | Principal/key validation and scope | Yes | Fail closed if key cannot be validated; bounded cache only. |
| Gateway | Router | Route selection and provider invocation coordination | Yes/stream | Typed error or fallback according to policy. |
| Gateway | Billing | Usage and cost append | Prefer async after response | Durable event retry; request must not silently lose usage. |
| Gateway | Privacy | Masking and policy decision | Yes | Fail closed for high-risk policy; log-only for lower-risk policy. |
| Router | Provider | Adapter invocation | Yes/stream | Retry/fallback/circuit breaker. |
| Provider | Upstream | Provider-specific HTTP/SDK contract | Yes/stream | Adapter maps upstream errors and usage. |
| Console | Auth | Sessions, organization, keys, members | Yes | User-visible safe error. |
| Console | Catalog/Policy | Models, providers, routes, policies | Yes | Version conflict or validation error. |
| Console | Billing | Usage, invoices, budgets, alerts | Yes | Stale read is labeled; mutations fail safely. |
| Console | Marketplace | Catalog, installation, approvals | Yes | Installation blocked if permission or security state invalid. |
| Marketplace | Agent Runtime | Approved run request | Async preferred | Run state and failure event recorded. |
| All services | Event Bus | Versioned telemetry/audit/usage events | Async | Retry with backoff; dead-letter after limit. |

## 4. Runtime conventions

All Python services use Python 3.11+, asynchronous I/O, `httpx`, `asyncpg`, `redis.asyncio`, and structured JSON logs through `structlog`. Every request handler must carry correlation metadata. Exceptions should use the shared domain exception hierarchy and the gateway must map them to the public error schema.

Each service must expose:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check that confirms the process is running. |
| `GET /ready` | Readiness check that confirms required dependencies are usable. |
| `GET /metrics` | Prometheus-compatible metrics where the service is deployed with metrics enabled. |
| `GET /version` | Build version, commit, schema version, and service name without secrets. |

## 5. Gateway

### Responsibilities

The gateway authenticates the request, validates schema, enforces request size and rate limits, attaches a request ID, invokes policy and privacy checks, calls the router, handles streaming, emits usage/audit events, and returns the normalized response.

### Must not do

The gateway must not contain provider-specific protocol logic, direct database joins across domains, unbounded retries, raw prompt logging, or hard-coded commercial pricing.

### Scaling

The gateway is stateless and horizontally scalable. Use CPU, request rate, active streams, and latency as scaling signals. Streaming connections require connection limits, idle timeouts, and graceful termination on rollout.

## 6. Auth / Identity

The identity service owns account lifecycle, organization boundaries, membership, scopes, roles, API keys, service identities, invitations, MFA metadata, and session state. API keys are displayed once, stored only as hashes, and checked against active status, expiry, organization, project, scopes, model allowlist, rate limit, and budget.

### Migration rule

Any change to auth persistence requires an Alembic migration, rollback plan, fixture updates, and a tenant-isolation test. Auth and billing databases remain isolated.

## 7. Router / Aggregator

The router receives a normalized request plus principal and policy context. It loads eligible candidates from the catalog, filters by capability and policy, scores candidates, selects a route, invokes provider through the provider contract, and records route-decision evidence. The router must separate deterministic policy filtering from optional scoring and never allow an optimization score to bypass a hard policy.

## 8. Provider

The provider service owns a registry of adapters. An adapter must implement model discovery metadata, request translation, non-streaming invocation, streaming invocation, embeddings where supported, usage normalization, error mapping, health check, capability declaration, and pricing reference.

A provider key is referenced by secret name and key field, never passed as a browser value. The provider service must not write upstream secrets to logs or error payloads.

## 9. Billing / Usage

Billing owns the append-only usage ledger and pricing calculations. It must accept idempotent usage events, store the applied price version, distinguish upstream usage from customer charge, apply credits and discounts, and expose read models for dashboards. Corrections are adjustment events.

## 10. Privacy

Privacy begins as a bounded module called by the gateway before routing. When policy complexity, throughput, or independent scaling justifies extraction, it becomes a separate service. The module must expose `evaluate`, `transform`, and `restore` operations with request-scoped context and must emit a privacy decision event.

## 11. Marketplace and agent runtime

Marketplace handles package lifecycle and approvals. Agent runtime handles execution and must be isolated from the control plane. The runtime must use a narrow gateway client for model calls and a permission broker for tools. Agents do not receive raw provider keys or unrestricted network access.

## 12. Service ownership template

Each service team must maintain:

| Artifact | Required content |
|---|---|
| README | Purpose, local run, configuration, dependencies, endpoints, owner, escalation. |
| Contract | OpenAPI or typed contract, error behavior, compatibility rules. |
| Data ownership | Tables/schemas, migrations, retention, backup, access role. |
| Tests | Unit, contract, integration, security, failure behavior. |
| Observability | Metrics, traces, logs, dashboards, alerts, runbook links. |
| Deployment | Image, resource requests/limits, probes, secrets, rollout, rollback. |
| Security | Threats, permissions, data classification, dependency and image scanning. |

## 13. Communication rules

Synchronous calls are limited to the request path and control-plane mutations. Usage, audit, analytics, and non-critical notifications are asynchronous. A service must not block a user request on an analytics warehouse write. If an event cannot be delivered, it must be retried and dead-lettered with enough metadata to replay safely.
