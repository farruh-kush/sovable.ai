# Solvable Code Quality and Debugging Guide

**Author:** Farruh

## Purpose

This guide defines the conventions used to keep the Solvable platform readable, diagnosable, and safe to change. The repository is organized by ownership: runtime domain code lives under `microservices/`, shared stable code lives under `backend/shared/`, browser applications live under `frontend/`, AI policy assets live under `ai/`, and cross-service validation lives under `testing/`.

## Service code conventions

Each microservice keeps its application code in `src/<service_name>/`, service-local tests in `tests/`, and packaging metadata in its own `pyproject.toml`. Public functions should have type annotations and a short docstring that explains the contract, not the implementation. Comments should explain why a non-obvious decision exists, especially around provider differences, masking, retries, timeouts, migrations, and security boundaries.

A service should raise domain-specific exceptions at its boundary. Adapter code may translate provider-specific failures into the shared exception hierarchy, while transport and infrastructure failures should retain enough context for diagnosis. Avoid a bare or broad `except Exception` unless the boundary is deliberately designed as a last-resort safety boundary; in that case, log the exception with a stable event name and re-raise or return an explicit degraded state.

## Logging and diagnostics

All services use structured logging through `ai_routing_shared.utils.get_logger`. Log event names should be stable snake-case identifiers such as `redis_health_check_failed`, and fields should be structured values such as `service`, `request_id`, `provider`, `model`, `latency_ms`, `status_code`, and `error_type`. Never log API keys, access tokens, prompt contents, activation tokens, raw PII, or provider secrets.

Health endpoints should distinguish `healthy` from `degraded` and should record the dependency failure reason in structured logs. A degraded health response must not hide a configuration error silently. Streaming parsers should catch only the parse error they expect; transport, authentication, and upstream errors must remain visible to the caller and logs.

## Local validation

Run the complete backend suite from the repository root:

```bash
./testing/scripts/run_tests.sh
```

Run frontend checks from `frontend/dashboard`:

```bash
npm run typecheck
npm run build
```

Render deployment manifests before applying them:

```bash
kubectl kustomize infrastructure/k8s/overlays/alibaba
kubectl kustomize infrastructure/k8s/overlays/aws
```

Review whitespace and the final worktree before committing:

```bash
git diff --check
git status --short
```

## Debugging workflow

Start with the request ID and service boundary. Confirm the gateway route and status code, then inspect the downstream service logs using the same request ID. For routing issues, record the selected policy, candidate models, rejected candidates, route reason, fallback count, provider, and latency. For masking issues, inspect entity categories and placeholder counts only; never inspect or log original sensitive values. For authentication issues, trace the registration or activation state using a redacted user identifier and challenge status, never the raw activation token.

For frontend issues, reproduce with a cache-busting query string, inspect the browser console and network request status, then verify the corresponding static asset exists in `frontend/dashboard/site`. Keep interactive actions non-blocking and provide an explicit empty, loading, error, or success state.

## Review checklist

Before merging a change, confirm that the implementation has a clear owner, stable paths, focused comments, structured diagnostics, no credential material, deterministic tests, and a documented rollback or failure mode. The backend test suite, frontend typecheck/build, Kustomize render, and `git diff --check` should all pass.
