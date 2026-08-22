# Solvable AI Test Plan and Release Work

**Author:** Farruh

## Purpose

This document summarizes the validation surface for the five independently deployable services, the shared backend library, the static dashboard, and the whole-platform release gate. The stream ownership matrix is maintained in [`docs/PROJECT_STREAM_ALIGNMENT.md`](docs/PROJECT_STREAM_ALIGNMENT.md).

The repository’s service tests are real deterministic tests rather than placeholder assertions. They run without production provider credentials and are organized beside the owning service.

## Test layers

| Area | Location | Required checks |
|---|---|---|
| Shared contracts and privacy | `backend/shared/tests/` | Pydantic validation, hashing, error mapping, masking and restoration |
| Auth / Identity | `microservices/auth/tests/` | API-key lifecycle, identity/session rules, activation and validation behavior |
| Billing / Usage | `microservices/billing/tests/` | Pricing, markup, usage persistence, idempotency and spend behavior |
| Gateway | `microservices/gateway/tests/` | Auth propagation, request validation, rate limits, budget and upstream errors |
| Provider adapters | `microservices/provider/tests/` | Adapter registry, normalization, retry classification, circuit behavior and health |
| Router / Aggregator | `microservices/router/tests/` | Static/dynamic candidate ordering, latency optimization, policy filtering and masking |
| Dashboard / Web Console | `frontend/dashboard/` | TypeScript strict check, lint, production static build and browser smoke checks |
| Infrastructure and release | `testing/scripts/` and `infrastructure/k8s/` | Secret scan, Python compilation, Kustomize render, rollout and rollback checks |

## Local validation

```bash
# Backend and shared tests
./testing/scripts/run_tests.sh

# Python style checks
make lint

# Dashboard checks
make frontend-checks

# Full repository release gate
./testing/scripts/release_gate.sh
```

The full gate uses synthetic content, deterministic service tests, and repository-local configuration. It does not call live upstream providers, capture payments, or use production keys. A staging integration run may add provider fakes, real PostgreSQL and Redis/Valkey containers, migration checks, browser smoke tests, bounded load tests, and failure injection.

## Whole-platform acceptance matrix

The release candidate is ready only when the following behaviors are tested together: Gateway authentication and API-key scope; Auth activation, session, RBAC, rotation, and revocation; Router policy selection, masking, cache behavior, fallback, streaming, embeddings, and provider health; Provider normalization, timeout, retry, and circuit behavior; Billing usage events, pricing, idempotency, quotas, and read APIs; dashboard route guards, four portals, App Store actions, UZ/RU/EN localization, accessibility, responsive behavior, loading/empty/forbidden/error states; observability and correlation; migration and restore safety; Kubernetes manifest rendering; image architecture; secret hygiene; smoke, resilience, and rollback evidence.

## Release evidence

Each candidate should record the tested commit, service and frontend artifact identifiers, configuration version, migration result, test commands, pass/fail output, known exceptions with owner and expiry, deployment environment, rollback trigger, and post-release monitoring result. The evidence must not contain API keys, access keys, session secrets, payment credentials, raw customer prompts, or unredacted provider responses.

## Remaining work before production promotion

The repository checks are now aligned with the seven engineering streams, but production promotion still requires environment-specific evidence. This includes a fresh non-production deployment, real migration and restore rehearsal, provider sandbox or approved test credentials held outside Git, browser-level checks against a deployed build, bounded load and failure-injection tests, an image scan/SBOM/signature process, configured SLO alerts, cost caps, backup ownership, and an approved rollback plan. Payment capture remains disabled until a contracted acquirer, merchant credentials, signed callbacks, settlement rules, refund rules, and production test evidence are configured.
