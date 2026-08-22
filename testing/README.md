# Testing

**Author:** Farruh

This directory contains cross-service test orchestration and platform validation utilities. Service-local tests remain beside each service under `microservices/<service>/tests`, while shared-library tests remain under `backend/shared/tests`.

Run the consolidated service suite with `./testing/scripts/run_tests.sh`. Whole-platform integration, security, load, failure, migration, and release-readiness evidence should be stored here or in the engineering handoff documentation.
