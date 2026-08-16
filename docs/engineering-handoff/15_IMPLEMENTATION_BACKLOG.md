# Solvable Implementation Backlog

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Prioritization model

Priorities are based on customer safety, revenue correctness, production reliability, and ability to unlock the next vertical slice. P0 blocks launch or creates material security/financial risk. P1 delivers product-ready control-plane capability. P2 improves differentiation, scale, and advanced intelligence.

## 2. P0 foundation epics

| Epic | Vertical slice | Primary owner | Acceptance gate |
|---|---|---|---|
| P0-1 Identity | Register/login, session, org, project, scoped API key, revoke. | Auth | Cross-tenant and revoked-key tests pass. |
| P0-2 Unified API | Chat, embeddings, models, normalized errors, SSE. | Gateway | OpenAI-compatible contract and smoke tests pass. |
| P0-3 Provider adapters | Model Studio/Qwen plus one second provider behind adapter interface. | Provider | Mock contract, timeout, retry, usage normalization pass. |
| P0-4 Router | Static mapping, policy allowlist, candidate selection, fallback. | Router | Deterministic route-decision evidence and no policy bypass. |
| P0-5 Privacy baseline | Credential detection, redaction/block, no raw request logging. | Privacy/Platform | Synthetic secret never reaches provider or telemetry. |
| P0-6 Usage ledger | Request usage event, immutable ledger, price version, budget check. | Billing | No double-charge; hard budget stop works. |
| P0-7 Production deploy | Kustomize overlays, TLS, health probes, migrations, rollback. | DevOps | ACK staging deploy and rollback evidence. |
| P0-8 Observability baseline | Request IDs, metrics, logs, provider health, critical alerts. | SRE | Traceable request and alert test. |

## 3. P1 product-ready epics

| Epic | Deliverable | Dependency |
|---|---|---|
| P1-1 Organization governance | Invitations, role administration, MFA, access review. | P0-1 |
| P1-2 User Panel | Overview, Playground, keys, models, usage, billing, team, privacy. | P0-1/P0-2/P0-6 |
| P1-3 Admin Panel | Organizations, providers, models, routing, billing ops, audit. | P0-1/P0-4/P0-6 |
| P1-4 Dynamic routing | Cost/latency/health scoring, route simulation, activation/rollback. | P0-4/P0-8 |
| P1-5 Data platform | Outbox, event schemas, curated facts, lineage, exports. | P0-6/P0-8 |
| P1-6 Reliability | Circuit breakers, backpressure, provider disablement, restore tests. | P0-4/P0-7 |
| P1-7 Billing maturity | Credits, invoices, reconciliation, adjustments, alerts. | P0-6 |
| P1-8 Marketplace governance | Signed manifest, scan, review, install, permission broker. | P0-1/P0-5/P0-7 |

## 4. P2 differentiation epics

| Epic | Deliverable |
|---|---|
| P2-1 Quality routing | Evaluation registry, task-specific quality signals, safe experiments. |
| P2-2 A/B routing | Cohorts, deterministic assignment, stop conditions, readout. |
| P2-3 Adaptive optimization | Constrained learning from cost, latency, quality, and reliability. |
| P2-4 Multimodal gateway | Image/audio/video contracts and provider capability governance. |
| P2-5 Enterprise federation | SSO, SCIM, domain verification, customer-managed keys. |
| P2-6 Advanced data platform | Warehouse connectors, metric store, lineage UI, data contracts. |
| P2-7 Marketplace ecosystem | Publisher self-service, revenue share, certification, app analytics. |

## 5. First 90 days

### Days 0–30: harden the deployed MVP

Freeze public contracts, add contract tests, eliminate credential exposure, verify all secrets are rotated, formalize migrations, add idempotency to mutations and billing, implement provider disablement, finish P0 observability, and run ACK restore/rollback drills. Close known dependency and image vulnerabilities.

### Days 31–60: product-control plane

Deliver User Panel and Admin Panel vertical slices, organization memberships, MFA for privileged users, dynamic route policies with simulation, budget alerts and billing read models, event outbox, privacy policy UI, and customer exports. Add staged releases and stronger network/secret controls.

### Days 61–90: production readiness and marketplace foundation

Deliver provider health automation, circuit breakers, reconciliation, SLO burn-rate alerts, signed app manifests, package scanning, installation approval, runtime permission broker, load testing, failure injection, security review, and a measured beta launch.

## 6. Suggested ownership

| Area | Accountable team |
|---|---|
| Gateway and public contracts | API Platform |
| Auth/RBAC and sessions | Identity |
| Router and policy | Routing Intelligence |
| Provider adapters and catalog | Provider Platform |
| Masking and privacy | Privacy Engineering |
| Billing and ledger | FinOps Platform |
| User/Admin Console | Product Engineering |
| Events and warehouse | Data Platform |
| Kubernetes, CI/CD, SLO | SRE/DevOps |
| Threat model and gates | Security |
| Contract, load, UAT | QA/Quality Engineering |
| Marketplace and runtime | Ecosystem Platform |

## 7. Definition of ready

A backlog item is ready when its user or operator outcome, API and data contract, owner, dependencies, policy impact, security classification, test plan, rollout/rollback plan, observability requirements, and acceptance criteria are clear.

## 8. Definition of done

An item is done when implementation, tests, migrations, documentation, telemetry, security gates, accessibility where applicable, deployment evidence, rollback evidence, and owner sign-off are complete. A feature is not done merely because it works on a developer laptop.

## 9. Release acceptance gates

Every release must pass unit/contract/integration/security checks; preserve tenant isolation; produce an SBOM and signed image; use immutable images; have migration and backup evidence; update dashboards and alerts; verify cost and budget behavior; and provide a rollback target. High-risk routing, privacy, billing, and marketplace changes require explicit approver sign-off.
