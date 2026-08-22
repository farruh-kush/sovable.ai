# AI Routing Layer — Implementation Plan

**Version:** 1.1  
**Date:** June 14, 2026  
**Based on:** Critical Review  
**Repository:** `k-farruh/ai-routing-platform`

---

## Overview

This document translates the findings of the critical review into a concrete, phased implementation plan. It is organised into four phases that mirror the original project specification's development stages, enriched with the specific gaps, bugs, and competitive feature recommendations identified in the review. Each phase contains discrete, independently deliverable tasks with clear acceptance criteria.

The plan is ordered by risk and business impact: **Phase 0** sets up the local development environment on your MacBook Pro at zero infrastructure cost; Phase 1 eliminates critical bugs that could cause financial loss or security breaches; Phase 2 makes the platform deployable on production infrastructure; Phase 3 closes the gap with market leaders like OpenRouter; and Phase 4 adds advanced intelligence and enterprise-grade features.

---

## Phase 0 — Local Development Environment (MacBook Pro, $0/month)

**Goal:** Get the full stack running locally on your MacBook Pro M1 Pro so you can develop, test, and iterate without any cloud infrastructure cost. All development work in Phases 1–3 should be done locally first.

**Target completion:** Day 1 (< 2 hours)

**Machine specs confirmed:** MacBook Pro 14-inch 2021, Apple M1 Pro, 16 GB RAM, macOS Tahoe 26.5.1

---

### Task 0.1 — Install Prerequisites

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Docker Desktop for Apple Silicon (ARM native — critical for M1)
brew install --cask docker
# Open Docker Desktop from Applications and complete the setup wizard
# Ensure "Use Rosetta for x86/amd64 emulation" is OFF in Docker settings

# Python 3.11 (matches the project's runtime)
brew install python@3.11

# Terraform CLI (install now, use later for cloud deployment)
brew tap hashicorp/tap && brew install hashicorp/tap/terraform

# Verify all tools
docker --version          # Docker Desktop 4.x
python3.11 --version      # Python 3.11.x
terraform --version       # Terraform v1.x
```

**Acceptance criteria:**
- `docker compose version` returns a valid version.
- `docker run --rm hello-world` completes successfully (ARM native, no Rosetta).

---

### Task 0.2 — Configure Environment Variables

```bash
cd /Users/farruhkushnazarov/Documents/AI-Projects/AI-Routing-Layer

# Create your local .env from the template
cp .env.example .env
```

Edit `.env` and fill in the following. Leave all `ALICLOUD_*` and `TF_VAR_*` fields empty for now.

| Variable | Where to get it | Required for local dev |
|---|---|---|
| `OPENAI_API_KEY` | platform.openai.com → API Keys | Yes (at least one provider) |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | Optional |
| `GOOGLE_API_KEY` | aistudio.google.com → API Keys | Optional |
| `MISTRAL_API_KEY` | console.mistral.ai → API Keys | Optional |
| `ADMIN_API_KEY` | Set any strong secret string | Yes |
| `SECRET_KEY` | Run `openssl rand -hex 32` | Yes |
| `DATABASE_URL` | Already set in docker-compose | Leave as-is |
| `REDIS_URL` | Already set in docker-compose | Leave as-is |
| `ALICLOUD_ACCESS_KEY` | Leave empty | Not needed locally |
| `ALICLOUD_SECRET_KEY` | Leave empty | Not needed locally |

**Acceptance criteria:**
- `.env` file exists and is not committed to Git (verify it is in `.gitignore`).
- At least `OPENAI_API_KEY` and `ADMIN_API_KEY` are set.

---

### Task 0.3 — Start the Full Stack

```bash
cd /Users/farruhkushnazarov/Documents/AI-Projects/AI-Routing-Layer

# Build and start all services (first run takes 2–3 minutes)
docker compose up --build

# Or run in background
docker compose up --build -d

# Check all containers are healthy
docker compose ps
```

This starts the following services, all running natively on Apple Silicon:

| Container | Port | Purpose |
|---|---|---|
| `api` | `localhost:8000` | FastAPI routing engine |
| `postgres` | `localhost:5432` | User, billing, usage database |
| `redis` | `localhost:6379` | Rate limiting, caching |
| `prometheus` | `localhost:9090` | Metrics collection |
| `grafana` | `localhost:3000` | Observability dashboard |

**Acceptance criteria:**
- `docker compose ps` shows all containers as `running` or `healthy`.
- `curl http://localhost:8000/health` returns `{"status": "healthy"}`.
- Grafana dashboard loads at `http://localhost:3000` (default login: `admin` / `admin`).

---

### Task 0.4 — Smoke Test End-to-End

```bash
# 1. Create a test API key
TEST_KEY=$(curl -s -X POST http://localhost:8000/v1/keys \
  -H "X-Admin-Key: $(grep ADMIN_API_KEY .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"name": "local-test", "tier": "free"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['key'])")

echo "Test key: $TEST_KEY"

# 2. List available models
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer $TEST_KEY"

# 3. Make a real chat completion (uses your OPENAI_API_KEY)
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $TEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Say hello in one word."}]}'

# 4. Check usage was recorded
curl http://localhost:8000/v1/usage \
  -H "Authorization: Bearer $TEST_KEY"
```

**Acceptance criteria:**
- Chat completion returns a valid OpenAI-format response.
- Usage record is created with correct token counts and cost.
- No errors in `docker compose logs api`.

---

### Task 0.5 — Development Workflow

For day-to-day development, use the following workflow to avoid full container rebuilds on every code change:

```bash
# Mount source code as a volume for hot-reload (add to docker-compose.yml if not present)
# The api service should have:
#   volumes:
#     - ./app:/app/app
#   command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Restart only the API container after code changes
docker compose restart api

# View live logs
docker compose logs -f api

# Run tests inside the container
docker compose exec api pytest tests/ -v

# Stop everything (data is preserved in Docker volumes)
docker compose stop

# Stop and delete all data (clean slate)
docker compose down -v
```

**Acceptance criteria:**
- A code change to `app/router/engine.py` is reflected in the running API within 2 seconds (hot-reload).
- `pytest` runs successfully inside the container.

---

### Local Development Cost Summary

| Item | Monthly Cost |
|---|---|
| Infrastructure (Docker on Mac) | **$0** |
| LLM API calls during testing | **~$5–20** (pay per actual test call) |
| **Total during development phase** | **~$5–20/month** |

> This compares to **$220–262/month** if you deployed to Alibaba Cloud Singapore from day one. Run locally until you hit the cloud deployment milestones listed in `ALIBABA_CLOUD_COST_ESTIMATE.md`.

---

## Phase 1 — Critical Bug Fixes & Policy Enforcement

**Goal:** Make the existing codebase correct and safe. No new features are shipped until these items are resolved, as they represent active financial and security risks.

**Target completion:** Sprint 1 (1–2 weeks)

---

### Task 1.1 — Fix Rate Limiter: Replace Fixed Window with True Sliding Window

**File:** `app/core/redis_client.py`

**Problem:** The current implementation calls `INCR` followed by `EXPIRE` in a pipeline. Because `EXPIRE` resets the TTL on every call, an active user's key never expires, eventually causing a permanent lockout once the limit is reached.

**Solution:** Replace with a Redis Sorted Set sliding window using timestamps as scores.

```python
# Correct sliding window implementation
async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    window_start = now - window_seconds
    async with self.client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, window_start)   # remove expired entries
        pipe.zadd(key, {str(now): now})                # add current request
        pipe.zcard(key)                                # count requests in window
        pipe.expire(key, window_seconds)               # set TTL for cleanup
        results = await pipe.execute()
    return results[2] <= limit
```

**Acceptance criteria:**
- A user sending requests at the rate limit boundary is correctly allowed and blocked.
- After the window elapses with no new requests, the key expires and the user is unblocked.
- Unit test covers the boundary condition and the expiry behaviour.

---

### Task 1.2 — Enforce Monthly Budget Cap Before Routing

**File:** `app/api/v1/chat.py` (pre-routing middleware hook)

**Problem:** `monthly_budget_usd` is stored in the `ApiKey` database model but is never read during request handling. Users can spend without limit.

**Solution:** Add a budget check in the request handler, before the routing engine is invoked.

```python
# In chat.py, after authenticating the API key:
if api_key.monthly_budget_usd is not None:
    current_spend = await usage_service.get_monthly_spend(api_key.id)
    if current_spend >= api_key.monthly_budget_usd:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "monthly_budget_exceeded",
                "message": f"Monthly budget of ${api_key.monthly_budget_usd:.2f} USD has been reached.",
                "spend": current_spend,
                "budget": api_key.monthly_budget_usd,
            }
        )
```

**Acceptance criteria:**
- Requests are blocked with HTTP 429 when the monthly spend meets or exceeds the budget.
- The error response body contains `spend` and `budget` fields for client-side display.
- Budget is checked atomically; concurrent requests at the limit do not cause over-spend.
- Unit and integration tests cover the enforcement and the pass-through case.

---

### Task 1.3 — Enforce Model Whitelist (`allowed_models`)

**File:** `app/api/v1/chat.py` or `app/router/engine.py`

**Problem:** `allowed_models` is defined in the `ApiKey` schema but is never checked. Any key can request any model regardless of its configured whitelist.

**Solution:** Add a model whitelist check immediately after authentication.

```python
# In chat.py, after authenticating the API key:
if api_key.allowed_models:
    if request.model not in api_key.allowed_models:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "model_not_allowed",
                "message": f"Model '{request.model}' is not permitted for this API key.",
                "allowed_models": api_key.allowed_models,
            }
        )
```

**Acceptance criteria:**
- Requests for a model not in `allowed_models` are rejected with HTTP 403.
- Keys with an empty or null `allowed_models` list have no restriction (backward compatible).
- Unit test covers both the allowed and blocked cases.

---

### Task 1.4 — Initialise Alembic Migrations

**Problem:** The application uses `Base.metadata.create_all` on startup. This is unsafe for production: schema changes cannot be rolled back, and concurrent deployments can corrupt the database.

**Solution:**
1. Run `alembic init alembic` to create the migrations directory.
2. Configure `alembic/env.py` to use the async SQLAlchemy engine and import all models.
3. Generate the initial migration: `alembic revision --autogenerate -m "initial schema"`.
4. Remove `create_all` from `app/main.py` startup.
5. Add `alembic upgrade head` to the Docker entrypoint before the application starts.

**Acceptance criteria:**
- `alembic upgrade head` runs cleanly on a fresh database.
- `alembic downgrade -1` reverts the last migration without error.
- `create_all` is removed from application startup code.
- CI pipeline runs migrations before the test suite.

---

## Phase 2 — Production Infrastructure Deployment

**Goal:** Deploy the platform to Alibaba Cloud using the Terraform modules added in the review. This phase makes the platform accessible at a real HTTPS endpoint.

**Target completion:** Sprint 2 (1 week)

---

### Task 2.1 — Create OSS Bucket for Terraform Remote State

This is a one-time manual step that must be completed before `terraform init` can succeed.

**Steps:**
1. Log in to the Alibaba Cloud console.
2. Create an OSS bucket named `llmrouter-tfstate` in your target region (e.g., `cn-hangzhou`).
3. Enable versioning on the bucket to protect state file history.
4. Ensure the RAM user whose AK/SK is in `.env` has `AliyunOSSFullAccess` on this bucket.

**Acceptance criteria:**
- `terraform init` completes without error.
- The state file appears in OSS after the first `terraform apply`.

---

### Task 2.2 — Populate `.env` with Alibaba Cloud Credentials

**File:** `.env` (local, never committed)

Add the following block to your `.env` file, using values from your Alibaba Cloud RAM console:

```bash
# Alibaba Cloud
ALICLOUD_ACCESS_KEY=<your-access-key-id>
ALICLOUD_SECRET_KEY=<your-access-key-secret>
ALICLOUD_REGION=cn-hangzhou

# Terraform sensitive inputs
TF_VAR_rds_password=<strong-password-min-16-chars>
TF_VAR_redis_password=<strong-password-min-16-chars>
TF_VAR_ssh_public_key=<contents-of-your-id_rsa.pub>
TF_VAR_ssl_certificate_id=   # leave blank for dev; set for prod
```

**RAM user minimum permissions required:**

| Permission Policy | Purpose |
|---|---|
| `AliyunECSFullAccess` | ECS Auto Scaling Group |
| `AliyunRDSFullAccess` | ApsaraDB RDS MySQL |
| `AliyunKVStoreFullAccess` | ApsaraDB Redis |
| `AliyunSLBFullAccess` | Server Load Balancer |
| `AliyunCRFullAccess` | Container Registry |
| `AliyunVPCFullAccess` | VPC, vSwitches, Security Groups |
| `AliyunNATGatewayFullAccess` | NAT Gateway, EIP, SNAT |
| `AliyunOSSFullAccess` | Terraform remote state bucket |

---

### Task 2.3 — Deploy Dev Infrastructure

```bash
# Install Terraform (one-time)
brew install terraform        # macOS
# snap install terraform      # Linux

# Deploy all Alibaba Cloud resources for dev
bash testing/scripts/deploy.sh dev
```

**What this provisions:**
- VPC with public + private vSwitches across 2 AZs
- NAT Gateway with EIP for private instance outbound access
- Security Groups with least-privilege rules
- ApsaraDB RDS MySQL 8.0 (private subnet, automated backups)
- ApsaraDB Redis 7.0 (private subnet)
- Container Registry namespace and repository
- ECS Auto Scaling Group (1 instance for dev)
- Internet-facing SLB

**Acceptance criteria:**
- `terraform apply` completes with zero errors.
- `terraform output api_endpoint` returns a valid public IP.
- RDS and Redis are reachable from within the VPC but not from the public internet.

---

### Task 2.4 — Build, Push, and Verify

```bash
# Build Docker image and push to ACR
bash testing/scripts/build-and-push.sh dev latest

# Verify the API is live
curl https://$(terraform -chdir=infrastructure/terraform output -raw api_endpoint)/health
```

**Acceptance criteria:**
- `/health` returns HTTP 200.
- `/v1/models` returns the list of configured providers.
- A test chat completion request succeeds end-to-end.

---

### Task 2.5 — Deploy Production Infrastructure

```bash
bash testing/scripts/deploy.sh prod
```

**Additional prod requirements before running:**
- Obtain an SSL certificate from Alibaba Cloud SSL Certificate Service and set `TF_VAR_ssl_certificate_id` in `.env`.
- Set `ecs_instance_count = 2` in `environments/prod/terraform.tfvars` (already set).
- Confirm the production confirmation prompt when prompted by the script.

---

## Phase 3 — Revenue-Generating Product Features

**Goal:** Close the competitive gap with OpenRouter by implementing the features that drive developer adoption and justify a platform markup. These features directly increase revenue.

**Target completion:** Sprints 3–5 (4–6 weeks)

---

### Task 3.1 — Client-Side Routing Controls (`provider` object)

**Inspired by:** OpenRouter's `provider` routing parameter

**Files to modify:** `app/models/schemas.py`, `app/router/engine.py`, `app/api/v1/chat.py`

Add an optional `provider` object to the `ChatCompletionRequest` schema:

```python
class ProviderPreferences(BaseModel):
    sort: Optional[Literal["price", "throughput", "latency"]] = None
    order: Optional[List[str]] = None          # e.g. ["openai", "anthropic"]
    allow_fallbacks: Optional[bool] = True
    data_collection: Optional[Literal["allow", "deny"]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    provider: Optional[ProviderPreferences] = None
    # ... existing fields
```

The routing engine must read `provider` preferences and apply them before the standard routing logic.

**Acceptance criteria:**
- `sort: "price"` routes to the cheapest available provider for the requested model.
- `sort: "latency"` routes to the provider with the lowest rolling average latency.
- `order: ["anthropic", "openai"]` tries Anthropic first, falls back to OpenAI.
- `allow_fallbacks: false` returns an error if the first provider is unavailable.
- All combinations are covered by integration tests.

---

### Task 3.2 — Prompt Caching Pass-Through

**Files to modify:** `app/providers/anthropic.py`, `app/providers/openai.py`, `app/providers/google.py`, `app/models/usage.py`

**Part A — Provider-native cache pass-through:**
- Forward Anthropic `cache_control` breakpoints in message content without stripping them.
- Forward OpenAI `cached_tokens` metadata from the response back to the client.
- Parse the provider's cache hit/miss signal from the response and store it in the usage log.

**Part B — Gateway-level exact-match caching:**
- Compute a cache key from `(model, messages_hash, temperature, max_tokens)`.
- On cache hit, return the cached response with a `X-Cache: HIT` header and zero provider cost.
- On cache miss, store the response in Redis with a configurable TTL.

**Part C — Usage log enrichment:**
Add `cached_tokens`, `cache_discount_usd`, and `cache_hit` fields to the `UsageRecord` model and the `/v1/generations` response.

**Acceptance criteria:**
- Anthropic `cache_control` messages are forwarded and the `cache_read_input_tokens` field is recorded.
- Two identical requests within the cache TTL return the second from cache with `X-Cache: HIT`.
- The usage log shows `cache_discount_usd > 0` for cached responses.

---

### Task 3.3 — Activity Logs API (`/v1/generations`)

**Files to create:** `app/api/v1/generations.py`

Expose a customer-facing endpoint that returns detailed metadata for a specific generation:

```
GET /v1/generations/{generation_id}
```

**Response schema:**

```json
{
  "id": "gen_abc123",
  "model": "gpt-4o",
  "provider": "openai",
  "created_at": "2026-06-13T10:00:00Z",
  "usage": {
    "prompt_tokens": 512,
    "completion_tokens": 128,
    "cached_tokens": 256,
    "total_tokens": 640
  },
  "cost": {
    "prompt_cost_usd": 0.00256,
    "completion_cost_usd": 0.00192,
    "cache_discount_usd": 0.00128,
    "total_cost_usd": 0.0032,
    "markup_usd": 0.000176,
    "billed_usd": 0.003376
  },
  "latency_ms": 843,
  "fallback_used": false,
  "cache_hit": true
}
```

**Acceptance criteria:**
- The endpoint is authenticated; users can only retrieve their own generations.
- All cost fields are accurate to 6 decimal places.
- The `generation_id` is returned in the `X-Generation-Id` response header of every chat completion.

---

### Task 3.4 — Data Policy and ZDR Routing

**Files to modify:** `ai/config/routing.yaml`, `app/router/engine.py`, `app/models/schemas.py`

**Part A — Tag providers in `routing.yaml`:**
```yaml
providers:
  openai:
    data_policy:
      zdr: false
      trains_on_data: false   # opt-out available via API settings
  anthropic:
    data_policy:
      zdr: true
      trains_on_data: false
  google:
    data_policy:
      zdr: false
      trains_on_data: true    # unless enterprise agreement
```

**Part B — Filter during routing:**
When `provider.data_collection: "deny"` is set in the request, the routing engine must exclude any provider where `trains_on_data: true` or `zdr: false`.

**Acceptance criteria:**
- A request with `data_collection: "deny"` never routes to a provider tagged `trains_on_data: true`.
- If no compliant provider is available, return HTTP 422 with a clear error message.
- Provider data policy tags are documented in the `/v1/models` response.

---

### Task 3.5 — OpenAI Responses API Endpoint (`/v1/responses`)

**Files to create:** `app/api/v1/responses.py`, `app/models/responses_schema.py`

Implement the `/v1/responses` endpoint to support OpenAI's Responses API format, which is the foundation for agentic and tool-use workflows.

**Key schema elements to implement:**
- `input`: Array of input items (text, image, file references)
- `output`: Array of output items with typed content blocks
- `tools`: Tool definitions for function calling
- `tool_choice`: Controls tool invocation behaviour
- Streaming via SSE with typed event objects (`response.created`, `response.output_item.added`, `response.completed`)

**Provider adapter updates required:**
- `openai.py`: Native pass-through (Responses API is natively supported)
- `anthropic.py`: Translate to Messages API format and back
- `google.py`: Translate to Gemini `generateContent` format and back

**Acceptance criteria:**
- A basic text request to `/v1/responses` returns a correctly shaped response object.
- Streaming returns well-formed SSE events in the correct order.
- The OpenAI Python SDK's `client.responses.create()` works against the platform without modification.

---

## Phase 4 — Advanced Intelligence & Enterprise Features

**Goal:** Implement self-optimising routing, observability infrastructure on Alibaba Cloud, and enterprise-grade features. These items complete the platform's transition from a routing proxy to a full AI infrastructure layer.

**Target completion:** Sprints 6–10 (6–8 weeks)

---

### Task 4.1 — Real Latency-Optimised Routing

**File:** `app/router/engine.py`

Replace the current stub (`# fall back to cost-optimized as a proxy`) with a real implementation that queries Redis for rolling latency averages.

**Design:**
- After every successful provider response, write the latency to a Redis Sorted Set keyed by `latency:{provider}:{model}` with a TTL of 5 minutes.
- The `_latency_optimized` routing method reads the rolling P50 latency from Redis and selects the provider with the lowest value.
- Fall back to cost-optimised routing if no latency data exists for a provider (cold start).

**Acceptance criteria:**
- After 10 requests to a provider, `sort: "latency"` routes to the provider with the lowest observed P50.
- Latency data older than 5 minutes is automatically evicted.
- Unit test mocks Redis and verifies correct provider selection.

---

### Task 4.2 — Observability Stack on Alibaba Cloud (ARMS Module)

**File:** `infrastructure/terraform/modules/arms/main.tf` (new module)

Replace the self-hosted Prometheus and Grafana containers in `docker-compose.yml` with Alibaba Cloud ARMS (Application Real-Time Monitoring Service), which provides a managed, Prometheus-compatible metrics backend.

**Resources to provision:**
- `alicloud_arms_prometheus` workspace
- Custom dashboard for: request rate, P50/P95/P99 latency per provider, error rate per provider, circuit breaker state, cost per key per day.
- Alert rules for: error rate > 5%, circuit breaker OPEN, monthly cost > 80% of budget.

**Acceptance criteria:**
- Metrics from the FastAPI application appear in the ARMS dashboard within 60 seconds.
- Alert fires when a simulated provider error rate exceeds 5%.

---

### Task 4.3 — A/B Testing Framework

**Files to modify:** `app/router/engine.py`, `ai/config/routing.yaml`

Allow traffic to be split between two models or providers for quality comparison.

**Configuration example in `routing.yaml`:**
```yaml
experiments:
  - name: gpt4o-vs-claude35
    traffic_split:
      - provider: openai
        model: gpt-4o
        weight: 50
      - provider: anthropic
        model: claude-3-5-sonnet
        weight: 50
    metrics:
      - latency_ms
      - cost_usd
      - user_feedback_score   # optional, via /v1/feedback endpoint
```

**Acceptance criteria:**
- Traffic is split within ±5% of the configured weights over 1,000 requests.
- Each request's experiment assignment is recorded in the usage log.
- A `/v1/experiments/{name}/results` endpoint returns aggregate metrics per variant.

---

### Task 4.4 — Structured Output Validation & Quality Tracking

**Files to modify:** `app/api/v1/chat.py`, `app/models/usage.py`

When a request includes a `response_format: { type: "json_schema", json_schema: {...} }` field, validate the model's response against the schema before returning it to the client.

- On validation failure, retry with the same or a fallback provider (up to 2 retries).
- Record `schema_validation_passed: bool` and `validation_retry_count: int` in the usage log.
- Expose per-provider validation failure rates in the ARMS dashboard.

**Acceptance criteria:**
- A request with a strict JSON schema returns a valid response or HTTP 422 after retries are exhausted.
- Validation failure rate is visible per provider in the observability dashboard.

---

## Summary: Prioritised Backlog

The following table consolidates all tasks into a single view, ordered by priority.

| ID | Phase | Priority | Task | Risk if Skipped | Effort |
|---|---|---|---|---|---|
| 0.1 | Local Dev | P0 | Install Docker Desktop + Terraform on Mac | Cannot run stack locally | XS |
| 0.2 | Local Dev | P0 | Configure `.env` with LLM API keys | No provider calls possible | XS |
| 0.3 | Local Dev | P0 | Start full stack via `docker compose up` | No local development environment | XS |
| 0.4 | Local Dev | P0 | Smoke test end-to-end locally | Unknown if baseline works | XS |
| 0.5 | Local Dev | P1 | Set up hot-reload dev workflow | Slow iteration cycle | XS |
| 1.1 | Bug Fix | P0 | Fix sliding window rate limiter | Users permanently locked out | S |
| 1.2 | Bug Fix | P0 | Enforce monthly budget cap | Unbounded cost leaks to providers | S |
| 1.3 | Bug Fix | P0 | Enforce `allowed_models` whitelist | Security bypass — any key can use any model | S |
| 1.4 | Bug Fix | P1 | Initialise Alembic migrations | Schema changes break production DB | M |
| 2.1 | Infra | P1 | Create OSS bucket for Terraform state | `terraform init` fails | XS |
| 2.2 | Infra | P1 | Populate `.env` with AK/SK | No cloud deployment possible | XS |
| 2.3 | Infra | P1 | Deploy dev infrastructure | Platform only runs locally | M |
| 2.4 | Infra | P1 | Build, push, verify on Alibaba Cloud | No live endpoint | S |
| 2.5 | Infra | P2 | Deploy production infrastructure | No production environment | M |
| 3.1 | Product | P1 | Client-side routing controls | Missing core developer UX vs OpenRouter | L |
| 3.2 | Product | P1 | Prompt caching pass-through | Missing primary cost-saving driver | L |
| 3.3 | Product | P1 | Activity Logs API (`/v1/generations`) | No per-request cost transparency | M |
| 3.4 | Product | P2 | Data policy and ZDR routing | Enterprise market inaccessible | M |
| 3.5 | Product | P2 | OpenAI Responses API (`/v1/responses`) | Incompatible with agentic SDKs | L |
| 4.1 | Advanced | P2 | Real latency-optimised routing | Routing spec incomplete | M |
| 4.2 | Advanced | P3 | ARMS observability module (Terraform) | Self-hosted Prometheus not scalable | L |
| 4.3 | Advanced | P3 | A/B testing framework | No model quality comparison capability | L |
| 4.4 | Advanced | P3 | Structured output validation | No quality tracking per provider | M |

**Effort key:** XS = < 1 day, S = 1–3 days, M = 3–7 days, L = 1–2 weeks

---

## Definition of Done

A task is considered complete when all of the following are true:

1. Code is merged to `main` via a reviewed pull request.
2. All acceptance criteria listed in the task are verified.
3. Unit and/or integration tests are added and passing in CI.
4. No new linting or type-checking errors are introduced.
5. The relevant section of `README.md` or API documentation is updated.
6. For infrastructure tasks: `terraform plan` shows zero diff after apply.

---

*This plan is a living document. Update it as tasks are completed, priorities shift, or new findings emerge from production usage.*
