# Solvable Test Strategy

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Quality objectives

Testing must prove that Solvable returns stable normalized contracts, enforces tenant and policy boundaries, routes safely, bills correctly, survives provider failure, protects sensitive data, and can be operated on Kubernetes. The test strategy combines fast local tests with realistic integration, failure-injection, security, load, data-quality, and user-acceptance tests.

## 2. Test pyramid

```text
                    UAT / Production-like drills
                 Load / Resilience / Security
              Integration / Migration / Data quality
          Contract / Adapter / API / Event compatibility
        Unit / Pure policy / Parsing / Formatting tests
```

The pyramid is a guide, not a reason to omit expensive tests for high-risk billing, privacy, auth, and routing code.

## 3. Unit testing

Unit tests cover pure policy evaluation, route filtering and scoring, retry classification, circuit transitions, masking detectors and transformations, token counting normalization, price calculation, budget decisions, RBAC permissions, pagination, error mapping, schema validation, event deduplication, and frontend state reducers.

Tests use deterministic clocks, seeded identifiers, synthetic content, and provider stubs. No unit test calls a production provider or requires a real secret.

## 4. Contract testing

Public APIs have OpenAPI/schema tests for request validation, response shape, error envelope, pagination, streaming events, and backward compatibility. Internal services use consumer-driven contract tests, Pact or an equivalent repository-based contract mechanism, for auth validation, route selection, provider invocation, usage publication, and event consumption.

Provider adapters implement a shared adapter contract. Each adapter must pass tests for normal chat, streaming, embeddings where supported, timeout, rate limit, invalid response, provider error, usage absence, malformed JSON, cancellation, and secret redaction.

Event contracts validate envelope fields, schema version, classification, tenant references, required payloads, and compatibility. Consumers must tolerate additive fields and reject incompatible versions safely.

## 5. Integration testing

The integration environment runs real PostgreSQL and Redis/Valkey containers, migrations, all relevant services, and provider mocks. The suite verifies:

- login, membership, project, key creation, rotation, revocation;
- gateway authentication, scope, rate limit, budget, and idempotency;
- router policy, masking, cache, fallback, and provider health;
- streaming from router through gateway to client;
- billing event, ledger, price version, and read model;
- event outbox, consumer retry, deduplication, and quarantine;
- marketplace manifest, permissions, installation, and run lifecycle;
- dashboard API integration and permission-driven states.

## 6. Security testing

Security gates include secret scanning, dependency and container vulnerability scanning, SBOM and signature verification, SAST, IaC/Kubernetes policy checks, dependency license checks, API fuzzing, authentication and session tests, authorization matrix tests, CSRF/CORS checks, SSRF tests, injection tests, export path tests, rate-limit bypass tests, and tenant-isolation tests.

LLM-specific security tests include prompt injection through user content, retrieved documents, tool results, model output, and app manifests; sensitive data exfiltration attempts; unsafe output rendering; tool argument smuggling; excessive agency; malicious connector requests; and cost-amplification prompts.

## 7. Load and performance tests

Use synthetic content and mocked providers first, then bounded provider sandbox tests. Scenarios include steady chat traffic, burst traffic, concurrent streams, embeddings batches, cache-heavy traffic, cache-miss traffic, provider latency increase, provider 429s, large but allowed prompts, many organizations/projects/keys, dashboard queries, and billing event backlog.

Measure gateway overhead separately from upstream latency. Verify p50/p95/p99, throughput, queue depth, CPU/memory, connection pool saturation, Redis latency, database locks, stream stability, and ledger timeliness. Load tests must have a hard cost cap and an expiry cleanup step.

## 8. Failure injection and resilience

Inject provider timeout, connection reset, 429, 5xx, malformed response, slow stream, credential rejection, DNS failure, Redis outage, database read-only state, event-bus delay, duplicate events, pod termination, node drain, ingress failure, certificate expiry simulation, and partial deployment.

Expected behavior is explicitly tested: retries are bounded, fallback respects policy, circuits open and recover, budgets do not bypass, streams do not duplicate silently, billing remains idempotent, and the User/Admin Panel shows degraded states.

## 9. Migration and recovery tests

Every migration runs on an empty database and a representative prior-version database. Test upgrade, application compatibility, backfill resume, duplicate rerun, partial failure, rollback/forward fix, backup restore, and schema checksum. A restored database must boot the application and pass smoke tests.

## 10. Data quality tests

Validate event uniqueness, required IDs, schema version, timestamps, tenant references, token arithmetic, price version, currency, ledger status transitions, route-decision linkage, privacy classification, warehouse row counts, dashboard freshness, and export field permissions. Data quality failures create test failures or data incidents; they do not get silently coerced.

## 11. User acceptance testing

UAT scenarios cover first registration/invitation, organization/project setup, key create/rotate/revoke, Playground chat and streaming, embeddings, model catalog, usage and cost, budget alert, privacy simulation, team role change, Admin provider disablement, route simulation/activation/rollback, audit search, marketplace install/run/stop, and export download.

UAT must include success, empty, loading, forbidden, validation error, dependency outage, stale data, and destructive-action confirmation states. Test on current supported Chromium, Firefox, Safari, desktop and tablet widths, keyboard navigation, and screen-reader landmarks.

## 12. Test data and privacy

Use synthetic names, tokens, credentials, documents, and payments. Any sanitized production-derived fixture requires approval, a documented transformation, and a short retention period. Test reports must not reproduce live keys or raw customer content.

## 13. CI gates and release evidence

| Gate | Required evidence |
|---|---|
| Pull request | Unit, type, lint, contract, secret scan. |
| Merge | Integration, migration, image scan, SBOM, manifest policy. |
| Staging | Smoke, browser, provider mock, performance sample, rollback rehearsal. |
| Production | Approval, signed digest, backup evidence, SLO/alert validation, release checklist. |
| Post-release | Error/latency/billing/privacy dashboard review and no-regression sample. |

## 14. Exit criteria

A release may proceed when all required tests pass, accepted exceptions have owners and expiry dates, no critical tenant-isolation or secret finding remains, migrations and restore evidence are complete, SLO dashboards are healthy, cost caps are configured, and rollback has been rehearsed for the affected risk class.
