# Alibaba Cloud Monthly Cost Estimate
## AI Routing Layer — Singapore (`ap-southeast-1`) Region

> **Pricing basis:** Official Alibaba Cloud pay-as-you-go rates, Singapore region, June 2026.
> Subscription (1-month prepaid) saves ~15–20% on compute and database; 1-year saves ~30%.
> All prices in **USD**. LLM API costs are separate and depend on actual token usage.

---

## Development Strategy: Local First, Cloud Second

> **Recommendation:** Run the full stack locally on your MacBook Pro (M1 Pro / 16 GB / macOS) until the platform is feature-complete and tested. Only then deploy to Alibaba Cloud Singapore. This saves **$220–262/month** during the entire development phase.

### Local Development Environment (Cost: $0/month)

Your MacBook Pro M1 Pro with 16 GB RAM comfortably runs the entire stack via Docker Desktop for Apple Silicon.

| Service | Local equivalent | Notes |
|---|---|---|
| FastAPI app | Docker container (ARM native) | Hot-reload via `uvicorn --reload` |
| PostgreSQL 15 | `postgres:15-alpine` Docker image | Persistent via Docker volume |
| Redis 7 | `redis:7-alpine` Docker image | Persistent via Docker volume |
| Prometheus | `prom/prometheus` Docker image | Scrapes FastAPI metrics |
| Grafana | `grafana/grafana` Docker image | Dashboard on `localhost:3000` |
| NAT Gateway | Not needed — Mac has direct internet | LLM API calls go direct |
| SLB / EIP | Not needed — `localhost:8000` | No public endpoint needed |

**One-time setup on macOS:**

```bash
# 1. Install Docker Desktop for Apple Silicon
brew install --cask docker

# 2. Install Terraform (for when you are ready to deploy to cloud)
brew tap hashicorp/tap && brew install hashicorp/tap/terraform

# 3. Clone the project (already done)
cd /Users/farruhkushnazarov/Documents/AI-Projects/AI-Routing-Layer

# 4. Copy and configure environment variables
cp .env.example .env
# Edit .env — add your LLM API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
# Leave all ALICLOUD_* variables empty for now

# 5. Start the full stack
docker compose up --build
```

**Verify it is running:**

```bash
# Health check
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/v1/models

# Create a test API key
curl -X POST http://localhost:8000/v1/keys \
  -H "X-Admin-Key: $(grep ADMIN_API_KEY .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "tier": "free"}'

# Make a real chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-test-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]}'
```

### When to Move to Cloud

Move to Alibaba Cloud Singapore (S tier, ~$220/month) only when:

| Milestone | Why it triggers cloud deployment |
|---|---|
| All 4 provider adapters working | Need stable public endpoint for external testing |
| Auth + rate limiting verified | Ready for first real users |
| Usage tracking + billing accurate | Can start charging |
| First external user or team member | Need persistent, always-on environment |

### Local vs Cloud Cost Comparison

| Phase | Environment | Monthly Infrastructure Cost | LLM API Cost |
|---|---|---|---|
| **Development** | Local Mac | **$0** | Pay per test call (~$5–20) |
| **MVP / First users** | S tier (Singapore) | **~$220** | ~$50–120 |
| **Growth** | M tier (Singapore) | **~$390** | ~$500–1,200 |
| **Scale** | L tier (Singapore) | **~$720** | ~$5,000–12,000 |
| **Enterprise** | XL tier (Singapore) | **~$1,640** | ~$50,000–120,000 |

---

## Tier Definitions

Traffic tiers are defined by the three parameters that drive cost in an LLM routing platform:

| Tier | QPM (Queries/min) | TPM (Tokens/min) | Concurrent Users | Typical Use Case |
|---|---|---|---|---|
| **S — Small** | < 100 QPM | < 200K TPM | 1–50 | Dev / internal tools / MVP |
| **M — Medium** | 100–1,000 QPM | 200K–2M TPM | 50–500 | Early-stage SaaS / startup |
| **L — Large** | 1,000–10,000 QPM | 2M–20M TPM | 500–5,000 | Growth-stage product |
| **XL — Extra Large** | 10,000+ QPM | 20M+ TPM | 5,000+ | Enterprise / high-traffic platform |

---

## Infrastructure Cost by Tier

### S — Small (~$230/month)

| Service | Spec | Monthly Cost |
|---|---|---|
| **ECS** (API server × 1) | `ecs.c7.large` — 2 vCPU / 4 GiB | $72 |
| **RDS MySQL 8.0** | `rds.mysql.s2.large` — 2 vCPU / 4 GiB, 50 GB ESSD | $85 |
| **ApsaraDB Redis 7.0** | `redis.master.small.default` — 1 GiB master-replica | $30 |
| **NAT Gateway** | Pay-by-CU, ~1–2 CU/hr avg | $43 |
| **EIP** | BGP Multi-ISP, ~30 GB outbound/month | $11 |
| **SLB / CLB** | Pay-by-LCU, internet-facing | $20 |
| **ACR** (Container Registry) | Personal Edition | Free |
| **OSS** (Terraform state) | < 1 GB | $1 |
| **Total (pay-as-you-go)** | | **~$262** |
| **Total (1-month subscription on ECS+RDS+Redis)** | | **~$220** |

---

### M — Medium (~$530/month)

| Service | Spec | Monthly Cost |
|---|---|---|
| **ECS** (API server × 2, Auto Scaling min=1 max=2) | `ecs.c7.large` — 2 vCPU / 4 GiB × avg 1.5 | $108 |
| **RDS MySQL 8.0** | `rds.mysql.s3.large` — 4 vCPU / 8 GiB, 100 GB ESSD | $165 |
| **ApsaraDB Redis 7.0** | `redis.master.mid.default` — 4 GiB master-replica | $85 |
| **NAT Gateway** | Pay-by-CU, ~3–5 CU/hr avg | $60 |
| **EIP** | BGP Multi-ISP, ~100 GB outbound/month | $18 |
| **SLB / CLB** | Pay-by-LCU, internet-facing | $28 |
| **ACR** | Personal Edition | Free |
| **OSS** | ~2 GB | $1 |
| **Total (pay-as-you-go)** | | **~$465** |
| **Total (1-month subscription on ECS+RDS+Redis)** | | **~$390** |

---

### L — Large (~$1,100/month)

| Service | Spec | Monthly Cost |
|---|---|---|
| **ECS** (API servers × 3–4, Auto Scaling) | `ecs.c7.xlarge` — 4 vCPU / 8 GiB × avg 3 | $450 |
| **RDS MySQL 8.0** | `rds.mysql.s3.large` — 4 vCPU / 8 GiB, 300 GB ESSD, HA | $220 |
| **ApsaraDB Redis 7.0** | `redis.master.large.default` — 8 GiB master-replica | $155 |
| **NAT Gateway** | Pay-by-CU, ~10–15 CU/hr avg | $90 |
| **EIP** | BGP Multi-ISP, ~500 GB outbound/month | $47 |
| **SLB / CLB** | Pay-by-LCU, internet-facing | $45 |
| **ACR** | Enterprise Basic | $9 |
| **OSS** | ~10 GB + logs | $5 |
| **Total (pay-as-you-go)** | | **~$1,021** |
| **Total (1-year subscription on ECS+RDS+Redis)** | | **~$720** |

---

### XL — Extra Large (~$2,500+/month)

| Service | Spec | Monthly Cost |
|---|---|---|
| **ECS** (API servers × 6–10, Auto Scaling) | `ecs.c7.2xlarge` — 8 vCPU / 16 GiB × avg 6 | $1,080 |
| **RDS MySQL 8.0** | `rds.mysql.c2.xlarge` — 8 vCPU / 32 GiB, 500 GB ESSD, HA | $480 |
| **ApsaraDB Redis 7.0** | `redis.master.2xlarge.default` — 16 GiB master-replica | $290 |
| **NAT Gateway** | Pay-by-CU, ~30–50 CU/hr avg | $175 |
| **EIP** | BGP Multi-ISP, ~2 TB outbound/month | $170 |
| **SLB / CLB** | Pay-by-LCU, internet-facing | $90 |
| **ACR** | Enterprise Standard | $45 |
| **OSS** | ~50 GB + logs | $15 |
| **Total (pay-as-you-go)** | | **~$2,345** |
| **Total (1-year subscription on ECS+RDS+Redis)** | | **~$1,640** |

---

## LLM API Call Cost by Tier

These costs are **entirely separate** from infrastructure and depend on which models you route to. The table below uses a **realistic model mix** for a routing platform (60% budget models, 30% mid-tier, 10% premium) and assumes a 3:1 output-to-input token ratio per request.

### Assumed model mix and blended cost

| Model | Tier | Input / 1M tokens | Output / 1M tokens | Traffic share |
|---|---|---|---|---|
| GPT-5.4-nano / Gemini 3.1 Flash-Lite | Budget | $0.20 | $1.25 | 60% |
| GPT-5.4-mini / Claude Haiku 4.5 | Mid-tier | $0.75 | $4.50 | 30% |
| GPT-5.4 / Claude Sonnet 4.6 | Premium | $2.50 | $15.00 | 10% |
| **Blended effective cost** | | **~$0.52/1M in** | **~$3.15/1M out** | 100% |

> With **prompt caching** (Anthropic: 90% off cached tokens; OpenAI: 10× cheaper cached input), real blended input cost drops to **~$0.15–0.30/1M tokens** for workloads with repeated system prompts.

### LLM API monthly cost estimates

| Tier | Requests/month | Avg tokens/request (in+out) | Total tokens/month | Est. LLM API cost |
|---|---|---|---|---|
| **S** | ~45,000 | ~1,500 | ~67M | **~$50–120** |
| **M** | ~450,000 | ~1,500 | ~675M | **~$500–1,200** |
| **L** | ~4,500,000 | ~1,500 | ~6.75B | **~$5,000–12,000** |
| **XL** | ~45,000,000 | ~1,500 | ~67.5B | **~$50,000–120,000** |

> **Note:** At L and XL scale, intelligent routing (cheapest-model-first, prompt caching, fallback chains) can reduce LLM API costs by **40–70%**. This is the core value proposition of the platform.

---

## Total Monthly Budget (Infrastructure + LLM API)

| Tier | Infrastructure | LLM API (mid estimate) | **Total** |
|---|---|---|---|
| **S** | ~$220 | ~$85 | **~$305/month** |
| **M** | ~$390 | ~$850 | **~$1,240/month** |
| **L** | ~$720 | ~$8,500 | **~$9,220/month** |
| **XL** | ~$1,640 | ~$85,000 | **~$86,640/month** |

> At L and XL tiers, **LLM API costs dominate** (93–98% of total spend). Infrastructure is a rounding error compared to token costs. This is why cost-optimised routing is the highest-priority feature to build.

---

## Cost Optimisation Levers

| Lever | Applicable Tier | Potential Saving |
|---|---|---|
| **1-year subscription** on ECS + RDS + Redis | All | 25–30% off infrastructure |
| **Prompt caching** (Anthropic, OpenAI, DeepSeek) | M, L, XL | 50–90% off repeated input tokens |
| **Model cascade routing** (cheap → expensive) | M, L, XL | 40–70% off LLM API costs |
| **Response caching** (Redis, identical prompts) | L, XL | 5–20% off total LLM calls |
| **Downsize RDS in S tier** to `rds.mysql.s1.small` | S | ~$40/month saved |
| **Use ACR Personal Edition** (free) | S, M | $9–45/month saved |
| **DeepSeek V4 Flash** as primary budget model | All | ~80% cheaper than GPT-5.4-nano |
| **Batch API** (Anthropic/OpenAI 50% off) | L, XL | 50% off non-real-time workloads |

---

## Key Pricing Facts — Singapore Region

| Service | Singapore Unit Price |
|---|---|
| ECS `ecs.c7.large` (2 vCPU / 4 GiB) | $0.097/hr (~$70/month) |
| ECS `ecs.c7.xlarge` (4 vCPU / 8 GiB) | $0.194/hr (~$140/month) |
| NAT Gateway instance fee | $0.043/hr |
| NAT Gateway CU fee | $0.043/CU/hr |
| EIP configuration fee | $0.006/hr/IP |
| EIP outbound traffic | $0.081/GB |
| SLB/CLB instance fee | $0.021/hr |
| SLB/CLB public IP retention | $0.006/hr |
| RDS storage (ESSD, outside China) | $0.0019/GB-hr |
| ACR Personal Edition | Free |
| ACR Enterprise Basic | ~$9/month |

---

## Terraform Variable Mapping

The `terraform.tfvars` files in the repository map directly to these tiers:

```hcl
# environments/dev/terraform.tfvars  → S tier
ecs_instance_type    = "ecs.c7.large"
ecs_instance_count   = 1
rds_instance_type    = "rds.mysql.s2.large"
redis_instance_class = "redis.master.small.default"

# environments/prod/terraform.tfvars → M tier (default)
ecs_instance_type    = "ecs.c7.xlarge"
ecs_instance_count   = 2
rds_instance_type    = "rds.mysql.s3.large"
redis_instance_class = "redis.master.mid.default"

# L tier — override for high-traffic production
ecs_instance_type    = "ecs.c7.xlarge"
ecs_instance_count   = 4          # Auto Scaling max
rds_instance_type    = "rds.mysql.s3.large"
redis_instance_class = "redis.master.large.default"

# XL tier — override for enterprise scale
ecs_instance_type    = "ecs.c7.2xlarge"
ecs_instance_count   = 8          # Auto Scaling max
rds_instance_type    = "rds.mysql.c2.xlarge"
redis_instance_class = "redis.master.2xlarge.default"
```

---

*Prices sourced from official Alibaba Cloud documentation (June 2026) and verified third-party benchmarks. LLM API prices sourced from provider official pages (June 9, 2026 via morphllm.com). Actual costs may vary ±10–15% based on exact traffic patterns, Auto Scaling behaviour, and promotional credits. Always verify on the [Alibaba Cloud Pricing Calculator](https://www.alibabacloud.com/pricing-calculator) before committing to a tier.*
