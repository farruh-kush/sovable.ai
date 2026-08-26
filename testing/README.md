# Testing

**Author:** Farruh

This directory contains cross-service test orchestration and platform validation utilities. Service-local tests remain beside each service under `microservices/<service>/tests`, while shared-library tests remain under `backend/shared/tests`.

Run the consolidated service and platform suite with `./testing/scripts/run_tests.sh`. The complete release matrix, thresholds, staging/ACK rules, rollback procedure, failure triage, and production PASS/NO-GO gate are documented in [`RELEASE_READINESS.md`](./RELEASE_READINESS.md). Deterministic fixtures live in `fixtures/`, the dependency-free external provider mock lives in `mocks/`, and sanitized JUnit/release evidence is written to `evidence/`. Whole-platform integration, security, load, failure, migration, and release-readiness evidence should be stored here or in the engineering handoff documentation. The default runner is read-only and must not target production.
