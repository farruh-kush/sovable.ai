# Solvable AI Project Structure

**Author:** Farruh

This repository is organized around independently deployable services and clear ownership boundaries.

```text
AI-Routing-Layer/
├── microservices/
│   ├── auth/
│   ├── billing/
│   ├── gateway/
│   ├── provider/
│   └── router/
├── backend/
│   ├── shared/                 # stable shared Python library and types
│   └── legacy-reference/       # retained earlier backend, not production runtime
├── frontend/
│   ├── dashboard/              # Next.js static-export console and public site
│   ├── docs-site/              # MkDocs documentation source and site
│   ├── legacy-client/           # retained earlier client template
│   └── legacy-site/             # retained earlier generated site
├── ai/
│   └── config/routing.yaml      # versioned routing/model policy catalog
├── testing/
│   └── scripts/run_tests.sh     # consolidated service test runner
├── infrastructure/
│   ├── k8s/                    # Kubernetes base and cloud overlays
│   └── observability/          # Prometheus, Grafana, Loki, and Promtail
├── tools/
│   ├── build/                  # reproducible build helpers
│   └── patches/                # non-runtime patch files
├── docs/                       # engineering handoff and product documentation
├── scripts/                    # repository setup utilities
└── docker-compose.yml          # local development stack
```

## Ownership rules

The five directories under `microservices/` own their domain contracts and service-local tests. The `backend/shared/` package contains only stable shared types, errors, middleware, serialization, and logging helpers. The `frontend/` directory contains browser-facing applications. AI policy assets belong under `ai/`; provider adapter implementation remains in `microservices/provider`. Cross-service validation belongs under `testing/`, while Kubernetes and observability assets belong under `infrastructure/`.

Generated exports and local caches remain inside their owning application directory and are not treated as source-of-truth code. Secrets, kubeconfig files, local environments, and runtime logs remain ignored and outside committed source.
