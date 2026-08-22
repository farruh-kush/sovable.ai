# Solvable AI Engineering Stream Alignment

**Author:** Farruh

## Purpose

This document is the repository source of truth for the seven independently testable engineering streams that make up the Solvable AI control plane. Each stream owns a clear implementation boundary, local tests, documentation, and release evidence. The five backend services communicate through HTTP contracts; shared Python models and middleware remain in `backend/shared/`.

## Stream map

| Stream | Implementation boundary | Tests and evidence | Dependency position |
|---|---|---|---|
| Gateway | `microservices/gateway/` | `microservices/gateway/tests/`, gateway contract and security checks | Parallel after contract baseline |
| Auth / Identity | `microservices/auth/` | `microservices/auth/tests/`, migrations, activation/session/RBAC evidence | Parallel after contract baseline |
| Router / Aggregator | `microservices/router/`, `ai/config/` | `microservices/router/tests/`, routing, masking, fallback, streaming, and resilience evidence | Parallel after contract baseline; consumes Provider contract |
| Provider adapters | `microservices/provider/` | `microservices/provider/tests/`, adapter fakes, normalized response/error evidence | Parallel after contract baseline; serves Router |
| Billing / Usage | `microservices/billing/` | `microservices/billing/tests/`, idempotency, pricing, ledger, quota evidence | Parallel after usage-event contract |
| Dashboard / Web Console | `frontend/dashboard/` | `npm run typecheck`, `npm run lint`, `npm run build`, browser smoke evidence | After public API contracts stabilize |
| Whole-platform release gate | `testing/`, `infrastructure/`, `.github/workflows/` | Full backend suite, frontend checks, manifest render, secret scan, smoke/load/resilience evidence | Final gate after candidate service and frontend artifacts exist |

## Shared ownership rules

`backend/shared/` contains only reusable backend contracts, exceptions, middleware, privacy utilities, and helpers. Service-specific behavior belongs in the owning `microservices/<name>/` directory. Routing policies, provider capability metadata, pricing, and tier constraints are configuration in `ai/config/routing.yaml`; they must not be hardcoded in service logic. PostgreSQL remains the persistent system of record, while Redis/Valkey is limited to ephemeral rate-limit, cache, latency, and spend-counter state.

The service boundary is intentionally narrow. Gateway authenticates and authorizes requests, Router selects and coordinates permitted targets, Provider translates provider-neutral requests, Billing records usage, and Auth owns identity and API-key lifecycle. No service may read another service’s database directly.

## Recommended dependency order

Gateway, Auth, Router, Provider, and Billing can progress in parallel when their HTTP contracts and shared models are stable. Router integration depends on the Provider adapter contract, and Billing integration depends on the usage-event contract emitted by the routing flow. The dashboard consumes the finalized Gateway, Auth, Router, Billing, and marketplace-facing contracts. Whole-platform validation starts only after candidate images, frontend build artifacts, migrations, configuration, and rollback references are available.

```text
Gateway ─┬─ Auth / Identity
         ├─ Router / Aggregator ─ Provider adapters ─ Upstream models
         └─ Billing / Usage
Frontend dashboard ─────── consumes stable public contracts
Whole-platform release ── validates all streams together
```

## Required checks

Every stream must pass its service-local tests and static checks without live provider credentials. Contract tests use deterministic fakes, synthetic content, and redacted fixtures. The release gate additionally checks frontend type safety and production build output, Kustomize rendering for Alibaba and AWS overlays, secret-pattern scanning, migration presence where schemas change, and immutable image references. No production deployment or live payment capture is implied by these repository checks.

The release evidence must record the tested commit, service and frontend artifact identifiers, configuration version, schema compatibility, test commands, pass/fail results, known exceptions with owners and expiry dates, and the rollback trigger. Credentials, tokens, customer prompts, raw provider responses, and production-derived data must not be stored in the repository or CI output.

## Local commands

```bash
# Backend unit and contract-oriented tests
./testing/scripts/run_tests.sh

# Python static checks
make lint

# Dashboard validation
cd frontend/dashboard
npm ci
npm run typecheck
npm run lint
npm run build

# Render deployment packages without applying them
kubectl kustomize infrastructure/k8s/overlays/alibaba
kubectl kustomize infrastructure/k8s/overlays/aws

# Whole release gate
./testing/scripts/release_gate.sh
```

## Handoff criteria

A service is ready for integration when its documented contract, deterministic tests, health/readiness behavior, redaction behavior, configuration example, deployment manifest, smoke procedure, and rollback notes are present. The frontend is ready when its typed API adapters, route states, accessibility checks, and production build are validated. The platform is release-ready only when all stream artifacts pass together, migration and restore evidence is available, secret and manifest checks are clean, observability signals are present, cost caps are configured, and rollback has been rehearsed for the affected risk class.
