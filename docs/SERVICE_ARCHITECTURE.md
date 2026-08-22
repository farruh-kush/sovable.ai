# AI Routing Layer - Architecture Reference

## System Overview

The **AI Routing Layer** is a professional-grade, microservice-based LLM routing platform that provides:

- **Unified API Gateway**: Single entry point for all client requests with authentication, rate limiting, and validation
- **Intelligent Routing Engine**: Dynamic provider selection based on cost, latency, and availability
- **Multi-Provider Support**: Seamless integration with OpenAI, Anthropic, and other LLM providers
- **Billing & Usage Tracking**: Comprehensive usage recording with cost calculation and quota enforcement
- **Observable & Reliable**: Full observability with metrics, distributed tracing, and structured logging
- **Scalable Infrastructure**: Cloud-native architecture supporting Kubernetes and multi-zone deployments

## Core Architecture Principles

### 1. **Service-Oriented Design**
The system is decomposed into focused, independently scalable services:

- **API Gateway Service**: HTTP request handling, authentication, validation
- **Routing Service**: Provider selection logic with dynamic scoring
- **Provider Service**: Unified interface for LLM providers
- **Billing Service**: Usage tracking and cost calculation
- **Auth Service**: OAuth, API keys, and access control
- **Observability**: Metrics, tracing, and logging infrastructure

### 2. **Clean Architecture**
```
┌─────────────────────────────────────────────────┐
│  API Layer (Controllers, HTTP Handlers)         │
├─────────────────────────────────────────────────┤
│  Business Logic (Services, Use Cases)           │
├─────────────────────────────────────────────────┤
│  Data Access & Integration (Repositories, DAO)  │
├─────────────────────────────────────────────────┤
│  Infrastructure (Database, Cache, External)     │
└─────────────────────────────────────────────────┘
```

### 3. **Dependency Injection**
Services depend on abstractions, not concrete implementations:
- Pluggable provider implementations
- Mock providers for testing
- Configurable storage backends
- Swappable observability collectors

### 4. **Error Handling & Resilience**
```
Request Flow
    ↓
Validate Input
    ↓
Call Provider (Attempt 1)
    ↓ (Failed)
Exponential Backoff Retry (Attempt 2-3)
    ↓ (Still Failed)
Fallback Provider (Alternative Provider)
    ↓
Return Error Response (All Failed)
```

## Project Structure

```
ai-routing-layer/
│
├── src/ai_routing_layer/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app initialization
│   ├── app_state.py                     # Global application state
│   │
│   ├── microservices/                        # ⭐ MICROSERVICE MODULES
│   │   ├── api_gateway/                # HTTP API & endpoints
│   │   │   ├── __init__.py
│   │   │   ├── routes.py               # FastAPI routers
│   │   │   └── dependencies.py         # Dependency injection
│   │   │
│   │   ├── routing/                    # Routing engine & logic
│   │   │   ├── __init__.py
│   │   │   └── engine.py               # Core routing logic
│   │   │
│   │   ├── providers/                  # LLM provider adapters
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Abstract provider interface
│   │   │   ├── openai.py               # OpenAI adapter
│   │   │   └── anthropic.py            # Anthropic adapter
│   │   │
│   │   ├── billing/                    # Billing & usage service
│   │   │   ├── __init__.py
│   │   │   └── service.py              # Billing logic
│   │   │
│   │   └── auth/                       # Authentication service
│   │       ├── __init__.py
│   │       ├── service.py              # Auth logic
│   │       └── rate_limit.py           # Rate limiting
│   │
│   ├── backend/shared/                         # ⭐ SHARED LIBRARIES
│   │   ├── models/                     # Domain models
│   │   │   ├── __init__.py
│   │   │   └── core.py                 # Data classes & Pydantic models
│   │   │
│   │   ├── exceptions/                 # Custom exceptions
│   │   │   └── __init__.py
│   │   │
│   │   ├── middleware/                 # HTTP middleware
│   │   │   └── __init__.py
│   │   │
│   │   └── utils/                      # Helper utilities
│   │       └── __init__.py
│   │
│   └── infrastructure/                 # ⭐ INFRASTRUCTURE & CONFIG
│       ├── config.py                   # Settings & configuration
│       ├── database/                   # Database layer
│       │   └── __init__.py
│       ├── cache/                      # Caching layer
│       │   └── __init__.py
│       └── observability/              # Metrics, tracing, logging
│           ├── __init__.py
│           ├── logging.py              # Structured logging
│           └── metrics.py              # Prometheus metrics
│
├── tests/                              # Test suite
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   └── e2e/                           # End-to-end tests
│
├── docs/                              # Documentation
│   ├── architecture.md                # Architecture guide (this file)
│   ├── SERVICE_ARCHITECTURE.md        # Detailed service docs
│   ├── DEPLOYMENT.md                  # Deployment guide
│   ├── API.md                         # API reference
│   └── images/                        # Architecture diagrams
│       ├── system-architecture.svg
│       ├── service-interactions.svg
│       ├── request-flow.svg
│       ├── data-model.svg
│       └── deployment-architecture.svg
│
├── docker/                            # Docker & container configs
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── docker-compose.yml
│
├── web/                               # Frontend & dashboard
│   ├── dashboard/                     # React/Next.js dashboard
│   └── marketing/                     # Marketing website
│
├── infrastructure/observability/                             # Infrastructure-as-Code
│   ├── kubernetes/                    # Kubernetes manifests
│   │   ├── base/
│   │   ├── overlays/
│   │   └── kustomization.yaml
│   │
│   └── terraform/                     # Terraform IaC
│       ├── main.tf
│       ├── variables.tf
│       └── environments/
│
├── pyproject.toml                     # Python project config
├── README.md                          # Quick start guide
└── .env.example                       # Environment template
```

## Service Architecture Details

### API Gateway Service
**Responsibility**: Handle all HTTP requests, validation, and authentication

**Files**:
- `microservices/api_gateway/routes.py` - Define FastAPI routes
- `microservices/api_gateway/dependencies.py` - Dependency injection setup

**Key Endpoints**:
```
POST   /v1/chat/completions         Chat completion requests
POST   /v1/embeddings                Embedding requests
GET    /v1/models                    List available models
POST   /v1/health                    Health check
GET    /v1/metrics                   Prometheus metrics
POST   /v1/keys                      Create API key (admin)
GET    /v1/keys                      List API keys (admin)
```

**Responsibilities**:
- Request validation (JSON schema, input constraints)
- Authentication (API key validation)
- Rate limiting (per-second, per-minute, per-day)
- Request ID generation for tracing
- Response formatting and error handling
- OpenAPI documentation generation

### Routing Service
**Responsibility**: Select optimal provider based on cost, latency, availability

**Files**:
- `microservices/routing/engine.py` - Core routing logic

**Core Logic**:
```python
def candidates_for_model(model: str) -> List[Provider]:
    # 1. Find routing config for model
    # 2. Get health status for each provider
    # 3. Score providers (cost + latency + availability)
    # 4. Sort by score
    # 5. Return ordered list for retry attempts
```

**Features**:
- Static routing (YAML configuration)
- Dynamic scoring (weighted multi-factor)
- Health-aware routing (skip unhealthy providers)
- Circuit breaker integration
- Fallback chains

### Provider Service
**Responsibility**: Abstract provider-specific APIs with unified interface

**Files**:
- `microservices/providers/base.py` - Abstract provider interface
- `microservices/providers/openai.py` - OpenAI implementation
- `microservices/providers/anthropic.py` - Anthropic implementation

**Interface**:
```python
class BaseProvider:
    async def chat(request: ChatCompletionRequest) -> ChatCompletionResponse
    async def chat_stream(request) -> AsyncIterator[ChatCompletionChunk]
    async def embeddings(request: EmbeddingRequest) -> EmbeddingResponse
    def estimate_tokens(text: str) -> int
    async def health_check() -> HealthStatus
```

**Features**:
- Request/response transformation
- Token counting and cost estimation
- Streaming support
- Rate limit enforcement
- Error handling & retries
- Health monitoring

### Billing Service
**Responsibility**: Track usage and calculate costs

**Files**:
- `microservices/billing/service.py` - Billing logic

**Key Operations**:
```python
def enforce_quota(api_key_id: UUID, daily_limit: Decimal) -> None
def enrich_usage(provider: str, model: str, usage: UsageInfo) -> UsageInfo
def record(usage_record: UsageRecord) -> None
```

**Features**:
- Usage record creation
- Cost calculation (per-token pricing)
- Quota enforcement
- Daily/monthly limit tracking
- Invoice generation
- Payment integration (Stripe)

### Auth Service
**Responsibility**: Authenticate requests and manage access control

**Files**:
- `microservices/auth/service.py` - Authentication logic
- `microservices/auth/rate_limit.py` - Rate limiting implementation

**Key Operations**:
```python
def validate_api_key(key: str) -> Principal
def validate_oauth_token(token: str) -> User
def check_rate_limit(principal: Principal) -> bool
def rotate_api_key(user_id: UUID) -> str
```

**Features**:
- API key validation and hashing
- OAuth 2.0 support (Google, GitHub, Apple)
- Rate limiting (in-memory or Redis)
- Quota enforcement
- Token refresh mechanisms
- Audit logging

## Data Flow

### Request Lifecycle

```
1. CLIENT REQUEST
   └─> SDK / Curl / Web UI
       └─> POST /v1/chat/completions + API Key

2. API GATEWAY
   └─> Validate request format
   └─> Extract and validate API key
   └─> Check rate limit (Redis)
   └─> Check authentication
   └─> Generate request ID (tracing)
   └─> Emit start metric

3. ROUTING SERVICE
   └─> Get candidates for model (from config)
   └─> Check provider health (Redis cache)
   └─> Score providers (cost + latency + availability)
   └─> Select primary provider + fallbacks

4. PROVIDER SERVICE (Attempt 1)
   └─> Call external API (OpenAI, Anthropic, etc.)
   └─> Handle response format
   └─> Count tokens
   └─> Emit provider metric
   └─> On error → Try fallback provider

5. BILLING SERVICE (Async)
   └─> Count tokens used
   └─> Calculate cost
   └─> Record usage (PostgreSQL)
   └─> Update quota
   └─> Emit billing metric

6. OBSERVABILITY
   └─> Record latency
   └─> Record provider success/failure
   └─> Emit distributed trace
   └─> Log request completion

7. RESPONSE
   └─> Format response (OpenAI-compatible)
   └─> Stream chunks (SSE)
   └─> Return to client
```

### Error Handling Flow

```
Provider Call Fails
    ↓
Check Retry Attempts
    ├─ Attempt < Max? → Exponential backoff + retry
    └─ Attempt >= Max? → Try fallback provider
        ├─ Fallback exists? → Call fallback
        └─ No fallback? → Return error response
            ├─ Format error (OpenAI-compatible)
            ├─ Log error with trace ID
            └─ Emit error metric
```

## Configuration Management

### Environment Variables

```bash
# API Configuration
APP_NAME=ai-routing-layer
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost/routing
DATABASE_POOL_SIZE=20

# Cache
REDIS_URL=redis://localhost:6379/0

# Authentication
OAUTH_CLIENT_ID=xxx
OAUTH_CLIENT_SECRET=xxx

# Provider APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Billing
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Observability
PROMETHEUS_PORT=9090
LOG_FORMAT=json
TRACE_SAMPLE_RATE=0.1
```

### Configuration File (routing.yaml)

```yaml
models:
  - name: "gpt-4o"
    primary: openai
    fallbacks: [openai-backup, anthropic]
    timeout_ms: 30000
    
  - name: "claude-3-5-sonnet"
    primary: anthropic
    fallbacks: [anthropic-backup]
    timeout_ms: 30000

routing_weights:
  cost: 0.4
  latency: 0.4
  availability: 0.2

providers:
  - name: openai
    type: openai
    base_url: https://api.openai.com/v1
    rate_limit: 3000
    health_check_interval: 60
```

## Observability Strategy

### Metrics (Prometheus)

```
# Request metrics
request_duration_seconds{endpoint, status}
request_total{endpoint, status}
request_errors_total{endpoint}

# Provider metrics
provider_response_time_ms{provider}
provider_success_total{provider}
provider_error_total{provider, error_type}
provider_rate_limit_hits{provider}

# Billing metrics
billing_usage_tokens{api_key, model, provider}
billing_cost_usd{api_key, model}
billing_quota_usage{api_key}

# System metrics
database_query_duration_seconds
cache_hit_ratio
worker_pool_size
```

### Tracing (OpenTelemetry)

```
POST /v1/chat/completions
├─ Span: api_gateway.validate
├─ Span: auth.validate_key
├─ Span: rate_limit.check
├─ Span: routing.select_provider
│  ├─ Span: provider_health.check
│  └─ Span: scoring.calculate
├─ Span: provider.chat
│  ├─ Span: openai.chat (external API call)
│  └─ Span: response.transform
├─ Span: billing.record
└─ Span: response.send
```

### Logging (Structured)

```json
{
  "timestamp": "2024-06-02T10:30:45Z",
  "level": "INFO",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "service": "api_gateway",
  "message": "Chat completion request",
  "request_id": "req_123",
  "user_id": "usr_456",
  "api_key_id": "key_789",
  "model": "gpt-4o",
  "provider": "openai",
  "status": "success",
  "latency_ms": 245,
  "tokens_used": 150
}
```

## Scaling Considerations

### Horizontal Scaling

**API Gateway Service**: Stateless, scales by number of concurrent requests
- Deploy 5-10 instances in production
- Use load balancer (Kubernetes Service)
- Each instance handles ~1000 req/sec

**Routing Service**: Can be co-located with API Gateway
- Uses in-memory cache (Redis) for health status
- Minimal CPU per request
- Scales with API Gateway

**Provider Service**: CPU-bound (token counting)
- 5-10 instances for high-throughput
- Each instance handles ~500 req/sec
- Use separate pod for token-heavy workloads

**Billing Service**: Can be split into hot/cold paths
- Hot path: In-memory recording → Redis queue
- Cold path: Batch processing → PostgreSQL (async)
- Use separate worker pool for batch processing

### Vertical Scaling

**Database**: PostgreSQL with connection pooling
- Pool size: 20-50 connections
- Use read replicas for query-heavy workloads
- Index: api_key_id, user_id, timestamp

**Cache**: Redis Cluster
- 3+ nodes for high availability
- Memory: 2-4 GB per node
- TTL: Provider health (30s), Rate limits (60s)

**Message Queue** (optional): RabbitMQ or AWS SQS
- Billing events
- Audit logs
- Notification delivery

## High Availability (HA)

### Single Points of Failure

| Component | Risk | Mitigation |
|-----------|------|-----------|
| API Gateway | High | Load balance across 3+ instances |
| PostgreSQL | High | Multi-AZ RDS with automatic failover |
| Redis | Medium | Cluster mode with sentinel |
| Provider APIs | Medium | Fallback chains, circuit breaker |
| DNS | Low | Cloud provider's highly available DNS |

### Disaster Recovery

| Scenario | RTO | RPO | Strategy |
|----------|-----|-----|----------|
| Single pod crash | 30s | 0s | Kubernetes auto-restart |
| Full node failure | 2min | 1min | Multi-zone deployment |
| Database corruption | 5min | 30s | Daily snapshots |
| Provider API outage | 10s | 0s | Fallback provider routing |
| Regional outage | 30min | 15min | Cross-region backup RDS |

## Monitoring & Alerting

### Critical Alerts

```
- Error rate > 1%              (5 min window)
- P95 latency > 1000ms         (5 min window)
- Provider success rate < 99%  (10 min window)
- Database connections near max (threshold: 80%)
- Cache hit ratio < 50%        (10 min window)
- Daily billing discrepancy    (5% variance)
```

### Dashboard Views

1. **System Health**: Overall status, error rates, latency
2. **Provider Status**: Health per provider, success rates, latencies
3. **User Metrics**: Top users, usage trends, cost breakdown
4. **Infrastructure**: Resource utilization, pod count, storage usage

## Testing Strategy

### Unit Tests
- Test each service independently
- Mock external dependencies
- Focus on business logic
- Target: 80%+ code coverage

### Integration Tests
- Test service interactions
- Use Docker Compose for dependencies
- Test API endpoints with real routing logic
- Target: Critical paths

### End-to-End Tests
- Test complete request lifecycle
- Use staging environment
- Test error scenarios and retries
- Test billing accuracy

### Load Tests
- Simulate production traffic
- Test auto-scaling triggers
- Test rate limiting
- Target: 10,000 req/sec per pod

## Security Considerations

### Authentication & Authorization
- API keys: hash + salt (bcrypt)
- OAuth: industry-standard (Google, GitHub, Apple)
- Token validation: in middleware
- RBAC: user role-based access control

### Data Protection
- Encryption in transit: TLS 1.3
- Encryption at rest: Database-level encryption
- Secrets management: Vault / AWS Secrets Manager
- PII: Minimal storage, automatic deletion

### API Security
- Rate limiting: Per-key, per-user, per-IP
- Input validation: JSON schema + Pydantic
- CORS: Origin-based access control
- WAF: Cloud provider WAF (AWS, CloudFlare)

### Audit & Compliance
- Audit logging: All user actions
- GDPR: Data deletion flows
- SOC2: Regular security audits
- Compliance: Documentation & checklists

## Next Steps

1. **Review Diagrams**: Examine architecture diagrams in `/docs/images/`
2. **Run Tests**: `pytest tests/ -v` to verify functionality
3. **Deploy**: Follow `/docs/DEPLOYMENT.md` for staging/production setup
4. **Monitor**: Set up Prometheus + Grafana dashboards
5. **Iterate**: Continuously optimize routing weights and resource allocation

## References

- **FastAPI**: https://fastapi.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/
- **SQLAlchemy**: https://www.sqlalchemy.org/
- **Kubernetes**: https://kubernetes.io/
- **OpenTelemetry**: https://opentelemetry.io/
- **Prometheus**: https://prometheus.io/
