# Solvable AI Routing Layer — Deployment Cost Estimate

**Author:** Farruh
**Prepared:** 2026-08-15
**Status:** Planning estimate; no cloud resources have been provisioned.

## Executive conclusion

For the first production-like deployment of the five-service platform, budget **approximately US$350–750 per month on Alibaba Cloud ACK** or **US$400–900 per month on AWS EKS**, excluding external model inference, taxes, support plans, and unusually high network egress. The lower end assumes one small production cluster, three small worker nodes, managed PostgreSQL and Redis/Valkey sized for an MVP, a single public ingress, and moderate logs. The upper end assumes high availability for the databases/cache, higher observability retention, and more headroom for scaling.

The external model bill is a separate variable cost. Using 100,000 requests per month, 1,200 input tokens and 400 output tokens per request, and a routing mix of 60% budget, 30% mid-tier, and 10% premium models, the planning example is **about US$378 per month before caching and tool charges**. Therefore, the initialThe external model bill  be treated as **US$728–1,128 per month on Alibaba Cloud** or **US$778–1,278 per month on AWS** for this illustrative traffic level. The model mix and token volume must be replaced with actual usage after a pilot.

> **Deployment gate:** This estimate is provided before deployment. I will not create or modify paid cloud resources until the target cloud, region, monthly ceiling, and deployment approval are confirmed.

## Assumptions

The estimate covers the current five-service architecture: Gateway, Auth, Router, Provider, and Billing, plus the dashboard. The first production-like environment uses one Kubernetes cluster, three worker nodes for failure tolerance, one managed PostgreSQL service with separate logical databases for Auth and Billing, one managed Redis-compatible cache, one public load balancer, private service-to-service networking, container registry storage, encrypted backups, and basic metrics/log retention.

The application does **not** include self-hosting a 100B-parameter Navo'i model in this estimate. GPU inference, model training, dedicated sovereign data-center capacity, and a national-scale App Store catalog would materially change the budget and are separate workstreams. The platform can route to an externally managed Navo'i-compatible endpoint or an internal provider adapter, but GPU capacity must be priced from the actual model, quantization, throughput, and residency requirement.

## Alibaba Clou## Alibabamate

Alibaba's official ACK documentation states that ACK managed Pro clusters incur a cluster-management fee of **US$0.09 per cluster-hour**, while Basic clusters do not have that management fee; both editions still incur the associated ECS, load-balancer, NAT/EIP, storage, registry, and observability charges. Exact prices vary by region and edition and must be confirmed in the Alibaba Cloud pricing calculator before purchase [1] [2].

| Alibaba Cloud component | MVP production assumption | Monthly planning range |
|---|---|---:|
| ACK managed cluster | Basic or Pro, one cluster | US$0–66 |
| ECS worker nodes | Three small general-purpose nodes, 2–4 vCPU each | US$150–330 |
| Managed PostgreSQL | Small instance, 50–100 GB encrypted storage, backups | US$80–180 |
| Managed Redis/Valkey | Small HA or replica-enabled cache | US$50–140 |
| SLB/ALB/NLB and public IPs | One public ingress plus API access | US$20–70 |
| NAT gateway and egress | Private workers pulling images and calling providers | US$30–100 |
| ACR, OSS, block storage | Images, backups, small assets | US$10–50 |
| Logs, metrics, alerts, tracing | Basic retention, not full enterprise SIEM | US$10–80 |
| **Estimated Alibaba infrastructure total** | Before tax and support | **US$350–750/month** |

The lower bound can be reduced by using ACK Basic, a single-zone development cluster, one small worker node, and self-managed PostgreSQL/Redis inside the cluster; that configuration is not the recommended production posture because it increases failure and operational risk. The estimate deliberately prices managed data services separately because database durability and backups are more important than minimizing the first invoice.

## AWS EKS estimate

AWS currently charges **US$0.10 per EKS cluster-hour** for Kubernetes versions under standard support, or roughly **US$73 per 730-hour month**. Extended support is **US$0.60 per cluster-hour**, so the cluster must be upgraded before it falls into extended support [3]. AWS separately charges for EC2 worker nodes, EBS, public IPv4 addresses, load balancing, RDS, ElastiCache/Valkey, logs, backups, and data transfer [3] [4] [5].

| AWS component | MVP production assumption | Monthly planning range |
|---|---|---:|
| EKS control plane | One cluster, standard support | US$73 |
| EC2 worker nodes | Three small general-purpose nodes | US$100–260 |
| RDS PostgreSQL | Small instance, 50–100 GB, backups | US$100–220 |
| ElastiCache/Valkey | Small cache, replica optional | US$40–140 |
| ALB/NLB, NAT gateway, public IPv4 | One public ingress and private egress | US$60–160 |
| ECR, EBS, S3, CloudWatch | Images, storage, logs and backups | US$20–90 |
| **Estimated AWS infrastructure total** | Before tax and support | **US$400–900/month** |

For a cost-sensitive pilot, an AWS single-AZ deployment with one node and smaller data services can be lower than this range, but it should be labeled development or staging. A multi-AZ production environment with RDS Multi-AZ, redundant cache nodes, higher log retention, or large egress can exceed the range.

## External model cost calculation

The model bill is driven by tokens, not Kubernetes node count. The calculation is:

```text
monthly model cost =
  (input_tokens / 1,000,000 × input_price_per_1M)
+ (output_tokens / 1,000,000 × output_price_per_1M)
+ tool/search/image/audio charges
```

The illustrative mix below uses current official published prices for representative models: Google Gemini 3.1 Flash-Lite at US$0.25 input and US$1.50 output per million tokens, Anthropic Claude Sonnet 4.6 at US$3 input and US$15 output, and OpenAIThe illustrative mix below uses current official published prices for re[6] [7] [8]. Provider prices, model aliases, and discounts can change; the routing catalog is therefore configuration-driven.

| Traffic share | Representative tier | Input $/1M | Output $/1M | Weighted input | Weighted output |
|---:|---|---:|---:|---:|---:|
| 60% | Budget: Gemini 3.1 Flash-Lite | 0.25 | 1.50 | 0.15 | 0.90 |
| 30% | Mid-tier: Claude Sonnet 4.6 | 3.00 | 15.00 | 0.90 | 4.50 |
| 10% | Premium: OpenAI gpt-5.6-terra | 2.00 | 12.00 | 0.20 | 1.20 |
| **Blended rate** | — | — | — | **US$1.25/1M input** | **US$6.60/1M output** |

At 100,000 requests per month, each with 1,200 input and 400 output tokens, monthly volume is 120 million input tokens and 40 million output tokens. The calculation is:

```text
120 × US$1.25 + 40 × US$6.60 = US$378/month
```

If prompt caching removes 30% of the input-token bill, the same example becomes approximately **US$340.20/month** before any tool or batch discounts. The platform's cost controls should enforce a per-key budget, per-tenant monthly cap, model allow-list, provider price snapshot, and alert threshold before requests are sent to an external provider.

## What is excluded

The estimate excludes VAT and other taxes, provider enterprise minimums, paid cloud support plans, domain registration or DNS transfeThe estimate excludes VAT and other taxes, provider enterprisene-tuning or training, large-scale data egress, private connectivity, 24/7 human operations, and commercial licensing for third-party models. The estimate excludes VAT and other taxes, provider enterprise minimums, paid or a dedicated national data center.

## Decision recommendation

For the first deployment, Alibaba Cloud ACK is the lower-cost planning baseline if the required region, account, and managed-service availability are acceptable. AWS EKS isFor the first deployment, Alibaba Cloud ACK is the lower-cost planning baseline if the required region, account, and managed-service availability are acceptable. AWS EKS isFor the first deployment, Alibaba Cloud ACK is the lower-cost planning baseline if the required region, account, and managed-service availability are acceptable. AWS EKS isFtions: the selected cloud, the target region, the maximum monthly infrastructure budget, and whether the first environment is a production-like pilot or a public production service. Until those are confirmed, work should remain in local testing and manifest preparation.

## References

[1]: https://www.alibabacloud.com/help/en/ack/ack-managed-and-ack-dedicated/product-overview/ack-pro-cluster-billing "Alibaba Cloud — Billing for ACK managed and dedicated clusters"
[2]: https://www.alibabacloud.com/help/en/ack/ack-managed-and-ack-dedicated/product-overview/billing-of-cloud-services "Alibaba Cloud — ACK cloud resource billing"
[3]: https://aws.amazon.com/eks/pricing/ "AWS — Amazon EKS pricing"
[4]: https://aws.amazon.com/rds/postgresql/pricing/ "AWS — Amazon RDS for PostgreSQL pricing"
[5]: https://aws.amazon.com/elasticache/pricing/ "AWS — Amazon ElastiCache pricing"
[6]: https://ai.google.dev/gemini-api/docs/pricing "Google — Gemini API pricing"
[7]: https://platform.claude.com/docs/en/about-claude/pricing "Anthropic — Claude API pricing"
[8]: https://developers.openai.com/api/docs/pricing "OpenAI — API pricing"
[9]: https://docs.mistral.ai/deployment/laplateforme/pricing/ "Mistral — API pricing"
