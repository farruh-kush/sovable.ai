# Solvable Data Model and Event Contracts

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Data ownership rules

PostgreSQL is the durable system of record for domain state. Auth owns identity and access tables in `auth_db`. Billing owns usage and financial tables in `billing_db`. No cross-database joins are permitted. Router, provider, privacy, and marketplace state may begin in the control-plane schema only if ownership remains explicit; as scale and team boundaries grow, each domain can move to a dedicated database without changing public contracts.

Redis/Valkey stores ephemeral data only: rate-limit counters, short-lived cache, provider health windows, idempotency locks, request-scoped state, and monthly spend cache. Redis data must have TTLs and a recovery behavior. No invoice, user, API key, audit, or usage ledger record may exist only in Redis.

## 2. Identifier and timestamp conventions

All IDs are opaque strings with a domain prefix, for example `org_01J...`, `req_01J...`, and `evt_01J...`. Timestamps are UTC RFC 3339. Database timestamps use timezone-aware types. Money uses integer minor units or fixed-precision decimal. Token counts are non-negative integers. Enumerations are lower snake case in APIs and database values.

## 3. Identity domain

### Core entities

| Entity | Key fields | Owner |
|---|---|---|
| `users` | `id`, email, status, display_name, verified_at, created_at, updated_at | Auth |
| `organizations` | `id`, name, slug, plan, status, residency, created_at | Auth |
| `workspaces` | `id`, organization_id, name, environment, status | Auth |
| `projects` | `id`, workspace_id, name, slug, status, budget_id | Auth |
| `memberships` | `id`, organization_id, user_id, role, status, invited_at, accepted_at | Auth |
| `service_identities` | `id`, organization_id, project_id, name, status, secret_ref | Auth |
| `api_keys` | `id`, project_id, name, prefix, secret_hash, scopes, expires_at, revoked_at, last_used_at | Auth |
| `sessions` | `id`, user_id, device, created_at, expires_at, revoked_at | Auth |
| `invitations` | `id`, organization_id, email, role, token_hash, expires_at, accepted_at | Auth |
| `mfa_factors` | `id`, user_id, type, secret_ref, verified_at, disabled_at | Auth |

### Identity invariants

A key belongs to one project and cannot cross organization boundaries. A user may belong to multiple organizations but must receive an explicit active membership in each. A role change is audited. A revoked key is rejected on the next validation call, subject to the documented cache-revocation window. API key plaintext is never stored.

## 4. Catalog domain

| Entity | Key fields | Owner |
|---|---|---|
| `providers` | `id`, slug, adapter_type, status, regions, data_policy, secret_ref | Catalog/Provider |
| `provider_endpoints` | `id`, provider_id, base_url, region, status, health_state | Catalog |
| `models` | `id`, provider_id, public_name, upstream_name, capabilities, context_window, status | Catalog |
| `model_capabilities` | `model_id`, chat, streaming, embeddings, tools, structured_output, modalities | Catalog |
| `price_versions` | `id`, provider_id, model_id, currency, input_rate, output_rate, cache_rate, effective_at, expires_at | Billing |
| `provider_health` | `provider_id`, endpoint_id, window, success_rate, p50, p95, error_rate, circuit_state | Router |

Catalog records are versioned. A model cannot be enabled for production without capability and price metadata or an explicit “unpriced/test-only” state.

## 5. Policy domain

| Entity | Key fields | Owner |
|---|---|---|
| `route_policies` | `id`, organization_id, project_id, name, status, active_version_id | Policy/Router |
| `route_policy_versions` | `id`, policy_id, version, rules, fallback_chain, created_by, approved_by, activated_at | Policy |
| `privacy_policies` | `id`, scope, name, status, active_version_id | Privacy |
| `privacy_policy_versions` | `id`, policy_id, version, classifications, actions, retention, providers | Privacy |
| `budget_policies` | `id`, scope, period, limit_minor, hard_stop, alert_thresholds | Billing |
| `rate_limit_policies` | `id`, scope, rpm, rph, concurrency, burst, hard_stop | Gateway/Auth |
| `policy_evaluations` | `id`, request_id, policy_id, version, decision, reasons, created_at | Event/Data |

Policies are immutable after activation. A new behavior creates a new draft version. Activation records the actor, approval, simulation result, and effective time.

## 6. Request and route domain

Request state may be split between hot operational data and events. The durable request envelope contains metadata, not raw prompt content by default.

| Entity | Key fields |
|---|---|
| `requests` | `id`, organization_id, project_id, key_id, endpoint, model_requested, status, started_at, completed_at |
| `provider_attempts` | `id`, request_id, provider_id, model_id, attempt_no, status, latency_ms, upstream_request_id |
| `route_decisions` | `id`, request_id, policy_version_id, candidates, filtered_candidates, selected_candidate, fallback_chain, reasons |
| `privacy_decisions` | `id`, request_id, policy_version_id, action, classes_detected, fields_transformed, provider_eligibility |
| `cache_events` | `id`, request_id, key_hash, state, ttl_seconds, tokens_saved |

Raw bodies, if explicitly retained, must be in an encrypted content store with tenant-specific access and a separate retention policy. They must not be placed in the relational request table.

## 7. Billing and usage domain

### Append-only usage ledger

| Field | Meaning |
|---|---|
| `ledger_event_id` | Unique idempotency key for a financial usage event. |
| `request_id` | Link to request envelope. |
| `organization_id`, `project_id`, `key_id` | Billing scope. |
| `provider_id`, `model_id` | Actual upstream target. |
| `price_version_id` | Pricing applied at calculation time. |
| `input_tokens`, `output_tokens`, `cached_tokens` | Normalized and raw usage where available. |
| `provider_cost_minor` | Upstream cost in minor currency units. |
| `platform_charge_minor` | Customer charge after markup, discounts, credits. |
| `currency` | ISO currency code. |
| `status` | `estimated`, `measured`, `reconciled`, `adjusted`, or `voided`. |
| `created_at` | Event timestamp. |

A correction is a new adjustment event that references the original. Delete and update operations are not allowed on finalized financial events.

## 8. Marketplace domain

| Entity | Key fields |
|---|---|
| `publishers` | `id`, owner, verification_status, support_contact, risk_level |
| `apps` | `id`, publisher_id, slug, name, type, visibility, status |
| `app_versions` | `id`, app_id, version, manifest_hash, artifact_ref, signature, compatibility, security_status |
| `app_permissions` | `id`, app_version_id, resource, action, scope, approval_required |
| `installations` | `id`, app_version_id, organization_id, project_id, status, config_ref |
| `app_runs` | `id`, installation_id, request_id, status, started_at, finished_at, cost_minor |
| `reviews` | `id`, app_id, organization_id, rating, text, status |
| `security_findings` | `id`, app_version_id, severity, finding, status, resolved_at |

A package is not installable unless its manifest is valid, artifact hash matches, signature is valid, publisher is approved, security state allows installation, and requested permissions fit the organization policy.

## 9. Event envelope

All asynchronous events use a common envelope:

```json
{
  "event_id": "evt_01J...",
  "event_type": "ai.request.completed.v1",
  "schema_version": "1",
  "occurred_at": "2026-08-16T12:00:00Z",
  "producer": "gateway",
  "environment": "production",
  "request_id": "req_01J...",
  "organization_id": "org_01J...",
  "project_id": "proj_01J...",
  "actor": {"type": "api_key", "id": "key_01J..."},
  "data_classification": "metadata_only",
  "payload": {},
  "trace": {"trace_id": "...", "span_id": "..."}
}
```

The envelope must be schema-validated before publish. Consumers must be idempotent on `event_id`. Unknown event types are quarantined rather than silently discarded.

## 10. Required event types

| Event | Producer | Consumer |
|---|---|---|
| `identity.user.created.v1` | Auth | Audit, analytics |
| `identity.membership.changed.v1` | Auth | Audit, policy cache |
| `identity.api_key.created.v1` | Auth | Audit |
| `identity.api_key.revoked.v1` | Auth | Gateway cache invalidation, audit |
| `ai.request.accepted.v1` | Gateway | Ops, analytics |
| `ai.request.completed.v1` | Gateway | Billing, analytics, audit |
| `ai.request.failed.v1` | Gateway | Billing if billable, ops, audit |
| `ai.route.decided.v1` | Router | Analytics, audit, route evaluation |
| `ai.provider.attempted.v1` | Provider | Ops, analytics, billing |
| `privacy.transformation.applied.v1` | Privacy | Audit, data lineage |
| `privacy.policy.blocked.v1` | Privacy | Audit, security alerts |
| `billing.usage.recorded.v1` | Billing | Invoice read model, reconciliation |
| `billing.budget.threshold.v1` | Billing | Alerts, admin UI |
| `marketplace.app.installed.v1` | Marketplace | Audit, policy cache |
| `marketplace.app.run.completed.v1` | Agent runtime | Billing, analytics, audit |
| `ops.provider.health.changed.v1` | Router/Provider | Routing cache, admin UI |
| `ops.deployment.changed.v1` | CI/CD | Audit, release dashboard |

## 11. Event retention and data quality

Operational events are retained according to environment and tenant policy. Financial and audit evidence has a longer retention schedule. Event payloads must be masked before publish. Data quality checks include non-null required IDs, valid schema version, valid tenant reference, non-negative token counts, known currency, known price version, and event-time sanity.

## 12. Database migration protocol

Every schema change includes an additive migration first, backfill if needed, application compatibility period, removal migration in a later release, test fixture update, rollback plan, and backup verification. Migrations run as a controlled deployment job and must not be automatically rerun against an unknown database.
