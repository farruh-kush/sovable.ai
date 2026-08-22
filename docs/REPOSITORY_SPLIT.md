# Solvable AI Repository Split and Service Server Map

**Author:** Farruh

## Decision

The Solvable AI platform remains available as an integration/reference repository, while each independently deployable runtime component receives its own GitHub repository. The split preserves HTTP service boundaries and makes each project task actionable without requiring engineers to search a monorepo for the service they own.

The shared contracts package is also extracted into a small dependency repository. It is not a network server and has no listening port. The whole-platform release stream receives a dedicated repository for contract tests, release gates, deployment validation, and integration evidence.

## Repository and server map

| Project stream | GitHub repository | Runtime/server | Port | Public or internal role | Primary dependencies |
|---|---|---|---:|---|---|
| Shared contracts | `sovable-shared-contracts` | Python package; no server | — | Internal package consumed by all backend services | Python 3.11+, Pydantic, structlog |
| Gateway | `sovable-gateway` | FastAPI Gateway Deployment / Service `gateway` | 8000 | Public API at `api.sovable.ai`; OpenAI-compatible entry point | Auth `8001`, Router `8002`, Billing `8004`, Redis/Valkey |
| Authentication | `sovable-auth` | FastAPI Auth Deployment / Service `auth` | 8001 | Internal identity, activation, sessions, API keys, RBAC | `auth_db`, DirectMail or approved email provider, shared contracts |
| Router / Aggregator | `sovable-router-aggregator` | FastAPI Router Deployment / Service `router` | 8002 | Internal policy engine, masking, routing, fallback, streaming | Provider `8003`, Billing `8004`, Redis/Valkey, routing catalog |
| Provider adapters | `sovable-provider-adapters` | FastAPI Provider Deployment / Service `provider` | 8003 | Internal adapter and normalization boundary | OpenAI, Anthropic, Google, Mistral credentials; shared contracts |
| Billing / Usage | `sovable-billing-usage` | FastAPI Billing Deployment / Service `billing` | 8004 | Internal usage ledger, pricing, quotas, cost controls | `billing_db`, Redis/Valkey, shared contracts |
| Dashboard / Web Console | `sovable-dashboard` | Next.js static output served by Nginx Deployment / Service `dashboard` | 8080 | Public `sovable.ai` UI and four portals | Gateway public API, Auth flows, static assets |
| Whole-platform testing and release | `sovable-platform-testing` | CI/release runner; no production server | — | Cross-service tests, smoke/load/resilience, Kustomize, rollback evidence | All service repositories, deployment environment, test doubles |

## Request path

```text
Client → api.sovable.ai:8000 Gateway
       → Auth :8001 for identity and API-key validation
       → Router/Aggregator :8002 for policy, masking, and target selection
       → Provider :8003 for upstream model execution
       → Billing :8004 for usage and cost events
       → Response normalization → Client

Browser → sovable.ai:8080 Dashboard → api.sovable.ai:8000 Gateway
```

The dashboard is the only frontend runtime. The Gateway is the only public backend runtime. Auth, Router, Provider, and Billing remain ClusterIP-only in Kubernetes and are not exposed directly through DNS or the public load balancer.

## Repository boundaries

Each runtime repository must include its own `README.md`, `AGENTS.md`, `Dockerfile`, package metadata, tests, health/readiness behavior, configuration example, CI workflow, and deployment contract. It may depend on the published `sovable-shared-contracts` package but must not read another service’s database or copy provider credentials.

The platform-testing repository consumes versioned service artifacts and repository references. It owns integration orchestration and release evidence but does not become a second implementation of service business logic. Kubernetes base and cloud overlays are maintained there unless a service-specific manifest is intentionally kept with the service and referenced by the release repository.

## Task routing rules

The Gateway task works only in `sovable-gateway` and validates server `8000`. The Auth task works only in `sovable-auth` and validates server `8001`. The Router/Aggregator task works only in `sovable-router-aggregator` and validates server `8002`. The Provider task works only in `sovable-provider-adapters` and validates server `8003`. The Billing task works only in `sovable-billing-usage` and validates server `8004`. The Frontend task works only in `sovable-dashboard` and validates Nginx server port `8080` plus the public domain. The Whole Platform task works in `sovable-platform-testing` and validates the complete `8000 → 8001/8002/8003/8004` path, dashboard integration, Kubernetes overlays, observability, rollback, and secret safety.

## Versioning and integration

Service repositories use immutable release tags and publish container images independently. The release repository pins the exact image tag or commit for every candidate. Shared-contract changes require a compatibility note and coordinated service test runs. A service may be developed and released independently, but the platform release gate must pass before a version is promoted to the shared Kubernetes environment.
