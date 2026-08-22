# Solvable AI Repository Structure

This document describes the implementation and ownership layout for the Solvable AI control plane.

**Author:** Farruh

```text
sovable.ai/
├── backend/
│   └── shared/                         # Reusable backend contracts and utilities
│       ├── pyproject.toml
│       ├── src/ai_routing_shared/
│       │   ├── models/                 # Canonical Pydantic request/response/usage models
│       │   ├── exceptions/             # Unified domain exception hierarchy
│       │   ├── middleware/             # Request IDs and error handling
│       │   ├── privacy/                # Data masking and restoration utilities
│       │   └── utils/                  # Logging and hashing helpers
│       └── tests/                      # Shared-library unit tests
│
├── microservices/                     # Independently deployable FastAPI services
│   ├── gateway/                        # Unified API entry point, auth proxy, limits
│   ├── auth/                           # Identity, activation links, sessions, API keys, RBAC
│   ├── router/                         # Policy evaluation, routing, masking, fallback, streams
│   ├── provider/                       # Provider adapters and response normalization
│   └── billing/                        # Usage ledger, pricing, quotas, and cost reporting
│       └── tests/                      # Each service owns its tests and fixtures
│
├── frontend/
│   └── dashboard/                      # Static Next.js dashboard and four-portal console
│       ├── pages/                      # Public, user, organization, creator, controller routes
│       ├── components/                 # Shared UI and architecture/pipeline components
│       ├── lib/                        # Typed API and authentication clients
│       ├── public/                     # Favicon and static assets
│       └── styles/                     # Responsive and localized UI styles
│
├── ai/
│   └── config/routing.yaml             # Provider registry, models, policies, pricing, tiers
│
├── testing/
│   ├── scripts/run_tests.sh            # Shared and microservice test runner
│   └── scripts/release_gate.sh         # Whole-platform local/CI release gate
│       └── secret_scan.py              # High-confidence tracked-secret scanner
│
├── infrastructure/
│   ├── observability/                  # PostgreSQL bootstrap, Prometheus, Grafana, Loki
│   └── k8s/                            # Base, cloud overlays, services, and reference package
│
├── docs/
│   ├── engineering-handoff/            # Architecture, contracts, security, DevOps, test strategy
│   └── PROJECT_STREAM_ALIGNMENT.md     # Seven stream ownership and handoff matrix
│
├── tools/                              # Safe repository maintenance utilities
├── docker-compose.yml                  # Local services and observability stack
├── Makefile                            # Local, build, deployment, and release commands
├── API_DOCS.md                         # Public and internal API overview
├── AGENTS.md                           # Repository contribution and safety rules
└── README.md                           # Product overview and getting started guide
```

## Service communication map

| Caller | Called | Protocol | Purpose |
|---|---|---|---|
| Gateway | Auth | HTTP REST | Validate API keys and propagate identity context |
| Gateway | Router | HTTP REST | Forward normalized chat and embedding requests |
| Gateway | Billing | HTTP REST | Read generation/usage status where required |
| Gateway | Redis/Valkey | TCP | Rate limiting, cache, and spend checks |
| Router | Provider | HTTP REST | Execute provider-neutral model requests |
| Router | Billing | HTTP REST | Emit asynchronous, idempotent usage events |
| Router | Redis/Valkey | TCP | Track latency, cache prompts, and provider health |
| Auth | PostgreSQL `auth_db` | TCP | Persist identities, sessions, and API-key records |
| Billing | PostgreSQL `billing_db` | TCP | Persist usage and billing records |
| Provider | External providers | HTTPS | Call configured upstream models through adapters |

## Ownership and boundary rules

The five microservices are isolated and communicate through HTTP contracts. No service reads another service’s database directly. `backend/shared/` contains reusable contracts and utilities only; business logic remains in its owning service. Routing and pricing behavior is configuration-driven from `ai/config/routing.yaml`, not hardcoded in application code. Redis/Valkey is ephemeral state and is never the persistent system of record.

The frontend consumes documented Gateway, Auth, Router, Billing, and marketplace contracts. It must not embed provider credentials or invent undocumented endpoints. `testing/` owns deterministic release checks and platform test orchestration, while `infrastructure/` owns deployment and observability packaging.

## Build and validation entry points

```bash
./testing/scripts/run_tests.sh
make lint
make frontend-checks
./testing/scripts/release_gate.sh
```
