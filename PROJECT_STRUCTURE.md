# AI Routing Layer — Project Structure

This document describes the microservice architecture directory layout.

**Author:** Farruh

```
ai-routing-platform/
│
├── shared/                          # Shared Python library (ai_routing_shared)
│   ├── pyproject.toml               # Shared library package definition
│   └── src/ai_routing_shared/
│       ├── models/                  # Canonical domain models (Pydantic v2)
│       │   ├── requests.py          # ChatCompletionRequest, EmbeddingRequest
│       │   ├── responses.py         # ChatCompletionResponse, EmbeddingResponse
│       │   ├── usage.py             # UsageRecord, GenerationRecord, UsageInfo
│       │   └── keys.py              # ApiKey, ApiKeyTier
│       ├── exceptions/              # Unified exception hierarchy
│       ├── middleware/              # RequestIdMiddleware, error_handler
│       └── utils/                   # Structured logging, hashing utilities
│
├── services/                        # Independently deployable microservices
│   │
│   ├── gateway/                     # API Gateway Service (port 8000)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/gateway/
│   │       ├── main.py              # FastAPI app factory
│   │       ├── core/
│   │       │   ├── config.py        # GatewaySettings
│   │       │   ├── auth.py          # Auth + rate limit + budget dependencies
│   │       │   └── redis_client.py  # Sliding window rate limiter (Phase 1.1)
│   │       └── api/v1/
│   │           ├── chat.py          # POST /v1/chat/completions
│   │           ├── embeddings.py    # POST /v1/embeddings
│   │           ├── models.py        # GET /v1/models
│   │           ├── keys.py          # POST/GET /v1/keys (admin)
│   │           ├── generations.py   # GET /v1/generations/{id}
│   │           └── health.py        # GET /health
│   │
│   ├── auth/                        # Auth & Identity Service (port 8001)
│   │   ├── Dockerfile               # Runs Alembic migrations on startup
│   │   ├── pyproject.toml
│   │   └── src/auth/
│   │       ├── main.py
│   │       ├── core/config.py
│   │       ├── db/
│   │       │   ├── database.py      # Async SQLAlchemy engine (no create_all)
│   │       │   └── models.py        # ApiKeyRecord ORM model
│   │       └── api/
│   │           ├── validate.py      # POST /internal/validate-key
│   │           └── keys.py          # POST/GET /internal/keys
│   │
│   ├── router/                      # Router Engine Service (port 8002)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/router/
│   │       ├── main.py
│   │       ├── core/
│   │       │   ├── config.py
│   │       │   └── redis_client.py  # P50 latency tracking (Phase 4.1)
│   │       ├── engine/
│   │       │   └── routing_engine.py  # All routing strategies
│   │       └── api/__init__.py      # POST /route/chat/completions, etc.
│   │
│   ├── provider/                    # Provider Adapter Service (port 8003)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/provider/
│   │       ├── main.py
│   │       ├── core/
│   │       │   ├── config.py
│   │       │   └── registry.py      # ProviderRegistry
│   │       ├── adapters/
│   │       │   ├── base.py          # BaseProviderAdapter + circuit breaker
│   │       │   ├── openai_adapter.py
│   │       │   └── anthropic_adapter.py
│   │       └── api/__init__.py      # POST /adapt/chat/completions, etc.
│   │
│   └── billing/                     # Billing & Usage Service (port 8004)
│       ├── Dockerfile               # Runs Alembic migrations on startup
│       ├── pyproject.toml
│       └── src/billing/
│           ├── main.py
│           ├── core/config.py
│           ├── db/
│           │   ├── database.py
│           │   └── models.py        # UsageRecordORM
│           ├── pricing/
│           │   └── catalog.py       # PricingCatalog with markup
│           └── api/
│               ├── usage.py         # POST /internal/usage
│               └── generations.py   # GET /internal/generations/{id}
│
├── config/
│   └── routing.yaml                 # Routing rules, pricing, tier policies
│
├── infra/
│   ├── postgres/
│   │   └── init-multiple-databases.sh
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── rules/alerts.yml
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── datasources/
│   │       └── dashboards/
│   ├── loki/
│   │   └── loki-config.yaml
│   └── promtail/
│       └── promtail-config.yaml
│
├── k8s/
│   ├── base/
│   │   ├── namespace.yaml
│   │   ├── hpa.yaml                 # Horizontal Pod Autoscalers
│   │   └── secrets.yaml.template
│   └── services/
│       ├── gateway.yaml             # Deployment + Service + Ingress
│       └── microservices.yaml       # auth, router, provider, billing
│
├── docker-compose.yml               # Full local development stack
├── .env.example                     # Environment variable template
├── README.md                        # Getting started guide
├── API_DOCS.md                      # API endpoint documentation
├── AGENTS.md                        # AI agent coding guidelines
└── PROJECT_STRUCTURE.md             # This file
```

## Service Communication Map

| Caller | Called | Protocol | Purpose |
|--------|--------|----------|---------|
| Gateway | Auth | HTTP POST | Validate API key on every request |
| Gateway | Router | HTTP POST | Forward validated requests |
| Gateway | Redis | TCP | Rate limiting, prompt cache, spend check |
| Router | Provider | HTTP POST | Execute LLM calls |
| Router | Billing | HTTP POST (async) | Emit usage events |
| Router | Redis | TCP | Record and read P50 latency |
| Billing | Redis | TCP | Update monthly spend counter |
| Auth | PostgreSQL (auth_db) | TCP | Read/write API key records |
| Billing | PostgreSQL (billing_db) | TCP | Read/write usage records |
