# Solvable AI Routing Layer — Implementation Status

**Author:** Farruh
**Date:** 2026-08-15
**Deployment state:** Not deployed. No paid cloud resources were created or modified.

## Completed in this workstream

The repository now has a working Russian-first public landing page and operations console with Overview, API-key management, and an OpenAI-compatible routing playground. The dashboard uses the gateway model catalog and health endpoints, supports a browser-saved API key/admin key for local administration, and builds successfully with Next.js 14.2.35.

The backend test surface now covers shared PII masking utilities, key generation and hashing, billing pricing and cache discounts, gateway cache-key and model-whitelist policies, routing chains and latency sorting, and provider adapter behavior. The Provider Service registers OpenAI, Anthropic, Google, and Mistral adapters. The repository test runner executes all service suites in one command.

Kubernetes packaging now includes a self-contained Kustomize base, an Alibaba ACK overlay, an AWS EKS overlay, public ingress patches for `api.solvable.ai`, a basic gateway egress NetworkPolicy, routing-catalog generation, and a deployment runbook. The overlays render successfully with the local Kubernetes client. Existing Prometheus, Grafana, Loki, Promtail, PostgreSQL, Redis, and Docker Compose assets remain available for local or operator-managed deployment.

## Verification results

| Check | Result | Evidence |
|---|---|---|
| Backend and shared tests | Passed: 37 tests | `./testing/scripts/run_tests.sh` |
| Python syntax compilation | Passed | Shared, router, and provider packages compiled |
| Dashboard strict type check | Passed | `npx tsc --noEmit` |
| Dashboard production build | Passed | `NEXT_TELEMETRY_DISABLED=1 CI=1 npm run build` |
| Kustomize Alibaba overlay | Passed | `kubectl kustomize infrastructure/k8s/overlays/alibaba` |
| Kustomize AWS overlay | Passed | `kubectl kustomize infrastructure/k8s/overlays/aws` |
| Docker image build | Blocked by environment | Docker CLI exists, but Docker Desktop daemon socket is unavailable |
| External provider live calls | Not attempted | No provider credentials were used or exposed |

## Remaining production gates

The first production environment still needs a cloud account and region, managed PostgreSQL and Redis/Valkey endpoints, provider credentials, a secret-manager integration, a certificate/ingress setup, a container registry namespace, DNS delegation for `api.solvable.ai`, and a decision on whether the first environment is a private pilot or public production. The current Kubernetes mThe first production environment still needs a cloud account and region, managed Poally.

The current streaming implementation remains the existing gateway-to-provider path and should be exercised in a live integration environment after cloud or local Docker availability is restored. The new masking utility is unit-tested and available for the privacy boundary, but provider-bound request mutation is intentionally not enabled globally until a tenant policy and restoration semantics are approved for production.

## Deployment approval required

Before any deployment action, approve the cloud and region, the maximum monthly infrastructure spend, the model-inference budget, and the public/private exposure. The planning ranges are documented in [`DEPLOYMENT_COST_ESTIMATE.md`](DEPLOYMENT_COST_ESTIMATE.md). The current recommendation is an Alibaba ACK pilot when the selected region and managed-service availability are acceptable; AWS EKS remains a fully packaged alternative.
