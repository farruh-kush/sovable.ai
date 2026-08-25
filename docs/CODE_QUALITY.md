# Solvable Code Quality and Debugging Guide

**Author:** Farruh

This guide defines the repeatable quality gate for the organized Solvable repository. The goal is code that is easy to read, safe to change, and straightforward to debug in local development and production incidents.

## Quality commands

Run `make quality` from the repository root. The command runs Python lint and formatting checks, the segregated backend test suite, frontend lint, TypeScript validation, and the static production build. For a focused check, use `make quality-python`, `./testing/scripts/run_tests.sh`, or `make -C frontend/dashboard typecheck`.

The Python checks use the root `ruff.toml`. FastAPI dependency declarations are intentionally excluded from the B008 rule because `Depends(...)` is the framework’s dependency-injection contract. The exception is documented in configuration rather than hidden with repeated inline suppressions.

## Debugging conventions

Every service uses structured logging through the shared logging helper. Request identifiers, provider names, generation identifiers, API-key identifiers, and user identifiers should be included when available; secrets and raw prompt content must never be logged. Provider adapters normalize upstream failures at the adapter boundary, while the gateway converts domain errors into the unified API error schema.

Background tasks are retained until completion so exceptions are not silently discarded. Best-effort billing emission is isolated from the client response path and logs a structured failure event. Transactional email errors are represented by the shared `EmailDeliveryError` domain exception before the authentication API maps them to an HTTP 503 response.

## Service-local workflow

Each microservice keeps its tests in `microservices/<service>/tests`. The shared package is under `backend/shared`. Cross-service orchestration belongs under `testing`, while deployment manifests and environment-independent configuration belong under `infrastructure` and `ai/config`.

Before committing a change, run the focused service tests, then the full quality gate. For a production issue, capture the request ID, service name, generation ID, provider, HTTP status, and sanitized error code before investigating logs.
