# AI Routing Layer — Technical Plan (editable)

> Goal: Build an OpenRouter-like LLM routing platform providing a hosted OpenAI-compatible API, multiple provider adapters, dynamic routing, SDKs (Python/JS), a public website and dashboard, billing, and observability.

## Principles
- Modular, incremental, and testable
- Security-first (API key hashing, rate limits, secret management)
- Cloud-native and automatable (IaC, CI/CD)
- Developer-friendly (OpenAPI, SDKs, playground)

## High-level architecture
- Public API Gateway (FastAPI behind a reverse proxy)
  - Authentication (API keys, OAuth)
  - Rate limiting, quota enforcement
  - Request validation (OpenAPI)
- Router Service (core)
  - Static & dynamic routing (cost/latency/availability scoring)
  - Provider adapters (OpenAI, Anthropic, others)
  - Retry / fallback / circuit-breaker logic
  - Streaming (SSE)
- Provider Adapters
  - Implement `BaseProvider` interface (async)
  - Pluggable registry and health checks
- Billing & Usage
  - Token counting, cost estimation, usage records
  - Stripe integration for payments
- Auth & Accounts
  - OAuth (Google/Apple/GitHub) and email sign-up
  - API key issuance & management (UI + API)
- Dashboard / Web UI
  - Marketing pages, docs, signup flows
  - Developer dashboard: keys, usage, billing, logs, playground
  - Admin console: providers, routing config, pricing
- SDKs & CLI
  - Python and JavaScript SDKs with streaming helpers and auth utilities
- Observability & Security
  - Metrics (Prometheus), Tracing (OpenTelemetry), Logs (structured JSON)
  - Alerts and abuse detection
- Infrastructure & Deployment
  - Docker for local dev, Kubernetes for prod (or managed services)
  - IaC (Terraform), CI (GitHub Actions)

  ## Diagrams

  Editable SVG diagrams are included in `docs/images/`. If your Markdown viewer does not render SVG inline, open the files directly from `docs/images/` or view them in a browser/vector editor.

  ### Architecture diagram

  <figure>
    <picture>
      <source srcset="/docs/images/architecture.png" type="image/png" />
      <img src="/docs/images/architecture.svg" alt="Architecture diagram: high level components" style="max-width:100%;height:auto" />
    </picture>
    <figcaption>High-level architecture diagram showing the API Gateway, Routing Service, Provider Adapters, Billing, Observability, Dashboard, SDKs, and Persistence. Use this to understand component boundaries and integrations.</figcaption>
  </figure>

  This diagram shows the high-level system components and their relationships:

  - API Gateway: handles authentication (API keys, OAuth), rate limiting, and request validation.
  - Routing Service: core decision-making for model→provider routing, dynamic scoring, retries, and circuit-breaking.
  - Provider Adapters: pluggable integrations for OpenAI, Anthropic, and other LLM providers (with health checks and streaming support).
  - Billing & Usage: token counting, cost estimation, and invoice/usage recording.
  - Observability and Persistence: metrics, tracing, logs, Postgres/Redis for state.

  ### Modules diagram

  <figure>
    <picture>
      <source srcset="/docs/images/modules.png" type="image/png" />
      <img src="/docs/images/modules.svg" alt="Modules diagram: logical modules map" style="max-width:100%;height:auto" />
    </picture>
    <figcaption>Modules diagram mapping logical components (Auth, Routing, Billing, Provider Adapters, Dashboard, Persistence). Useful for planning ownership and sprint tasks.</figcaption>
  </figure>

  This diagram maps the logical modules in the codebase to their responsibilities. Use it when planning development tasks or assigning ownership for sprints.

  Key modules:

  - `Auth Service`: OAuth and API key management, signup flows.
  - `Routing Engine`: dynamic routing policies and fallback logic.
  - `Billing`: usage collection and cost enrichment.
  - `Provider Adapters`: individual provider implementations and registry.

  ### Request flow diagram

  <figure>
    <picture>
      <source srcset="/docs/images/flow.png" type="image/png" />
      <img src="/docs/images/flow.svg" alt="Request flow diagram: client → gateway → router → provider" style="max-width:100%;height:auto" />
    </picture>
    <figcaption>Request flow diagram showing a client request progressing through the API Gateway, Routing Service, Provider Adapter, and Billing. Use when creating integration tests or tracing production requests.</figcaption>
  </figure>

  The flow diagram illustrates a sample request from client (SDK/Curl) through the API Gateway, routing decision, provider call, and billing recording. It is helpful when writing integration tests or tracing errors in production.

  If you'd like alternative formats (PNG exports, larger canvases, or editable source in Figma/SVG with layers), I can generate those as well.

## Modules & files (skeleton)
- backend/
  - api/ (FastAPI endpoints, documentation)
    - routes.py, dependencies.py
  - core/
    - router_engine.py, service.py
  - providers/
    - base.py, openai.py, anthropic.py, registry.py
  - auth/
    - oauth.py, keys.py, models.py
  - billing/
    - pricing.py, stripe.py, usage_store.py
  - observability/
    - metrics.py, tracing.py, logging.py
  - db/
    - migrations/, models.py
  - tests/
- sdk/
  - python/, js/
- web/
  - marketing/ (static), dashboard/ (React/Next.js)
- infra/
  - docker-compose.yml, k8s/, terraform/
- docs/
  - openapi.yaml, architecture.md (this file)

## UI / Frontend architecture

The project includes a lightweight dashboard and marketing frontend intended to be implemented with a Node.js React framework (Next.js). The frontend responsibilities are:

- Public marketing pages and docs (static, SEO-friendly)
- Developer dashboard (authenticated): API keys, usage, billing, logs, playground
- Admin console: manage providers, routing config, pricing
- Embedded SDK examples and interactive playground

Key frontend design principles

- Single codebase for marketing + dashboard using Next.js with pages/app router as appropriate
- Server-side rendering for marketing + static generation for docs
- Client-side rendering and streaming for playground and dashboard operations
- Auth flows: OAuth redirects for signup/login, and managed API key provisioning display
- Secure API communication: always use HTTPS and never expose provider API keys in the browser
- Reusable component library (Buttons, Forms, Modals, Tables, DataGrid, Charts)
- Accessibility and responsive UI (mobile-first)

Suggested folder layout for frontend (Next.js)

web/dashboard/
  - package.json
  - next.config.js
  - pages/ (or app/)
    - index.tsx (marketing / landing)
    - dashboard/index.tsx (main dashboard)
    - api/ (optional server-side helpers)
  - components/
    - Layout.tsx, Nav.tsx, ApiKeyList.tsx, UsageChart.tsx
  - lib/
    - api.ts (fetch helpers), auth.ts (client tokens)
  - styles/

Canvas and UX flow (high-level)

1. Landing / Signup
   - Marketing landing page explains the product and links to signup/login.
   - Signup initiates OAuth flow or email signup; after verification user receives an API key on success.
2. Dashboard - Keys
   - Show list of API keys: create, revoke, rotate (display raw key once on creation)
   - Allow applying per-key quotas and view usage/costs
3. Dashboard - Usage & Billing
   - Time-series charts of requests and cost (Prometheus + billing store)
   - Export usage CSV and invoice history
4. Dashboard - Routing & Providers
   - Visual editor (YAML or form-based) for routing rules
   - Provider health, latency, and error counts with controls to disable/enable
5. Playground
   - Interactive chat playground with streaming responses and provider chooser
   - Show token/cost estimates before or after execution

Developer notes

- The frontend should call the backend API at `/v1/*` endpoints described in the API surface. Long-running or streaming interactions should be proxied as server-side endpoints when provider secrets would otherwise be exposed.
- Build the dashboard incrementally; start with a minimal Next.js app that calls `/v1/health` and `/v1/chat/completions` using `dev-default-key` then add auth and key management.
- For design assets, maintain a simple Figma/Canva board with core screens: Landing, Signup, Dashboard Keys, Usage, Routing Editor, Playground.

If you'd like, I can scaffold a minimal Next.js project under `web/dashboard` with starter pages, components, and a README — ready to run with `npm install` and `npm run dev`.

## Core data models (conceptual)
- User { id, email, oauth_provider, role, created_at }
- APIKey { id, user_id, key_hash, created_at, revoked, metadata }
- UsageRecord { id, api_key_id, model, provider, tokens_in, tokens_out, cost_usd, ts }
- BillingInvoice, PaymentRecord, Plan
- ProviderHealth { provider, last_latency_ms, error_count, circuit_state }

## API surface (essential)
- POST /v1/chat/completions (OpenAI-compatible)
- POST /v1/embeddings
- GET/POST /v1/signup (OAuth + email)
- GET/POST /v1/keys (create/list/revoke API keys)
- GET /v1/health, /v1/metrics
- Admin API: /admin/providers, /admin/routing, /admin/users

> Deliver OpenAPI spec iteratively; start with chat + embeddings + auth endpoints.

## Auth & onboarding
- OAuth sign-in using Authlib (Google/Apple/GitHub) for production flows
- Email sign-up with verification as fallback
- After sign-up, issue a managed long-lived API key and show it once in dashboard
- Support key rotation and short-lived tokens if needed

## Billing & payments
- Pricing catalog per provider/model
- Track usage and estimate cost per request (billing enrichment)
- Stripe sandbox for payments, subscriptions, invoicing
- Quota enforcement based on daily $ limit and request quotas

## Routing & reliability
- YAML config for static routing (model→provider)
- Dynamic routing scoring: cost_weight, latency_weight, availability_weight
- Retries with exponential backoff; circuit breaker per provider; fallback chaining
- Hedged requests optional for critical low-latency paths

## SDKs & developer experience
- SDK features:
  - request helpers + streaming utilities
  - auth helpers for API key usage
  - typed responses (dataclasses / TypeScript types)
- CLI for key creation, usage export, simple playground calls

## Observability
- Prometheus metrics for request latencies, provider errors, usage
- OpenTelemetry tracing across calls to providers
- Structured logs (JSON) shipped to a log store (ELK or cloud)
- Health endpoints and dashboards (Grafana)

## Persistence
- PostgreSQL for production; SQLite for local dev
- Redis for rate-limiting and caching
- Migrations with Alembic

## Security & compliance
- Store only hashes/fingerprints of API keys
- Rate limiting, WAF, and abuse detection
- GDPR: data deletion flows and minimal PII storage
- Secrets in KMS/Vault

## Infra & CI/CD
- Local: docker-compose
- Prod: container images + Kubernetes or managed services
- IaC: Terraform for cloud resources
- CI: GitHub Actions (tests, lint, build image, publish SDK)
- CD: automated to staging; manual for production

## Milestones (suggested sprints)
- Sprint 0 (1 week): Scaffolding, basic FastAPI server, provider base, docker-compose
- Sprint 1 (2 weeks): Provider adapters (mock + OpenAI), routing engine, endpoints
- Sprint 2 (2 weeks): Auth + API key issuance, signup UI, in-memory usage
- Sprint 3 (2 weeks): SDKs skeleton (Python/JS) and examples
- Sprint 4 (2 weeks): Billing prototype + Stripe sandbox
- Sprint 5 (2–3 weeks): Dashboard + playground + docs
- Sprint 6+: Observability, infra, hardening, production rollout

## How the AI assistant will work with you
- Work iteratively on the plan above; you can edit any section and I’ll adapt
- For each sprint I will:
  1. Create/modify files with small, testable changes
  2. Run unit tests / linters where possible
  3. Start the service and run smoke tests
  4. Update docs and tests

## Next recommended immediate actions (choose one)
- A. Scaffold repo and local dev (pyproject, Dockerfile, docker-compose)
- B. Implement persistent API key storage (Postgres models + migrations)
- C. Implement OAuth provider integrations (Authlib wiring for Google/Apple)
- D. Start SDK skeleton (Python package + examples)

---

(You can edit this file directly — it’s intended to be a living plan.)
