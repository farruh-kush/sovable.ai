# Solvable Engineering Handoff Package

**Author:** Farruh  
**Version:** 1.0  
**Date:** 16 August 2026  
**Status:** Complete engineering kickoff package

## Purpose

This package translates the Solvable whole-platform BRD into an implementation-oriented set of documents for backend, frontend, data, security, QA, platform engineering, and operations teams. It is designed to answer four questions: what the platform does, where each capability lives, how services communicate, and how the platform is built, tested, deployed, secured, and operated.

The package deliberately separates the **current implementation baseline** from the **target platform increments**. The repository currently contains five Python services—gateway, auth, router, provider, and billing—plus a dashboard, shared library, Docker Compose environment, observability assets, and Kubernetes overlays. Privacy policy, data platform, agent/app store, and expanded organization control-plane capabilities are target increments and must be delivered through explicit contracts rather than tight coupling into existing services.

## Reading order by role

| Role | Start here | Then read |
|---|---|---|
| Engineering lead | `01_SYSTEM_ARCHITECTURE.md` | `02_SERVICE_CATALOG.md`, `15_IMPLEMENTATION_BACKLOG.md`, `16_DECISION_REGISTER.md` |
| Backend engineer | `02_SERVICE_CATALOG.md` | `03_API_CONTRACTS.md`, `04_DATA_MODEL_AND_EVENTS.md`, `05_ROUTING_SPEC.md`, `06_DATA_MASKING_SPEC.md` |
| Frontend engineer | `03_API_CONTRACTS.md` | `08_IDENTITY_RBAC_BILLING.md`, `09_USER_ADMIN_CONSOLE.md`, `15_IMPLEMENTATION_BACKLOG.md` |
| Data engineer | `04_DATA_MODEL_AND_EVENTS.md` | `10_DATA_PLATFORM.md`, `08_IDENTITY_RBAC_BILLING.md` |
| Agent/platform engineer | `07_AGENT_APP_STORE_SPEC.md` | `05_ROUTING_SPEC.md`, `06_DATA_MASKING_SPEC.md`, `10_DATA_PLATFORM.md` |
| DevOps/platform engineer | `11_DEVOPS_CICD_ENVIRONMENTS.md` | `12_KUBERNETES_RUNBOOK.md`, `13_OBSERVABILITY_SLO_ALERTS.md`, `14_SECURITY_THREAT_MODEL.md` |
| QA/SDET | `03_API_CONTRACTS.md` | `17_TEST_STRATEGY.md`, `05_ROUTING_SPEC.md`, `06_DATA_MASKING_SPEC.md`, `07_AGENT_APP_STORE_SPEC.md` |
| Security/privacy | `06_DATA_MASKING_SPEC.md` | `14_SECURITY_THREAT_MODEL.md`, `04_DATA_MODEL_AND_EVENTS.md`, `07_AGENT_APP_STORE_SPEC.md` |
| Product/project manager | `15_IMPLEMENTATION_BACKLOG.md` | `16_DECISION_REGISTER.md`, `01_SYSTEM_ARCHITECTURE.md`, the whole-platform BRD |

## Package contents

| File | Purpose |
|---|---|
| `01_SYSTEM_ARCHITECTURE.md` | Target architecture, service boundaries, data flows, deployment topology, and current-to-target transition. |
| `02_SERVICE_CATALOG.md` | Ownership, responsibilities, dependencies, runtime contracts, state, scaling, and repository mapping for every service. |
| `03_API_CONTRACTS.md` | Public API and internal service API conventions, endpoint contracts, errors, auth, idempotency, and versioning. |
| `04_DATA_MODEL_AND_EVENTS.md` | Logical entities, database ownership, event envelopes, usage ledger, audit events, and schema evolution. |
| `05_ROUTING_SPEC.md` | Router/aggregator policy model, candidate filtering, scoring, fallback, retries, circuit breakers, and explainability. |
| `06_DATA_MASKING_SPEC.md` | Sensitive-data detection, masking/tokenization/blocking, restoration, retention, policy evaluation, and tests. |
| `07_AGENT_APP_STORE_SPEC.md` | Agent, tool, connector, workflow, package manifest, publisher review, permissions, runtime isolation, and rollback. |
| `08_IDENTITY_RBAC_BILLING.md` | Organizations, workspaces, users, roles, API keys, quotas, budgets, pricing, and billing ledger rules. |
| `09_USER_ADMIN_CONSOLE.md` | User Panel and Admin Panel information architecture, screen requirements, permissions, and frontend states. |
| `10_DATA_PLATFORM.md` | Event ingestion, operational stores, warehouse exports, lineage, data quality, retention, and analytics. |
| `11_DEVOPS_CICD_ENVIRONMENTS.md` | Repository workflow, image build, CI/CD, environments, secrets, registries, release gates, and rollback. |
| `12_KUBERNETES_RUNBOOK.md` | ACK/EKS deployment, prerequisites, namespaces, migrations, ingress, TLS, DNS, health checks, rollback, and cleanup. |
| `13_OBSERVABILITY_SLO_ALERTS.md` | Metrics, traces, logs, dashboards, SLOs, alerts, provider health, cost signals, and incident evidence. |
| `14_SECURITY_THREAT_MODEL.md` | Threat model, trust boundaries, controls, abuse cases, secrets, agent threats, supply chain, and security gates. |
| `15_IMPLEMENTATION_BACKLOG.md` | Epics, vertical slices, priorities, dependencies, acceptance gates, suggested ownership, and first 90 days. |
| `16_DECISION_REGISTER.md` | Decisions already made, decisions required, defaults, owners, due dates, and consequences. |
| `17_TEST_STRATEGY.md` | Unit, contract, integration, security, load, failure-injection, migration, data-quality, and UAT strategy. |
| `diagrams/` | Mermaid sources and rendered architecture, request lifecycle, data-flow, deployment topology, and trust-boundary diagrams, plus visual verification notes. |
| `runbooks/` | Short operational procedures for incident response, provider disablement, credential rotation, and data recovery. |
| `contracts/` | Machine-readable contract examples for routing policy, provider adapter, masking policy, event envelope, and app manifest. |

## Engineering rules inherited from the repository

The five existing microservices remain isolated and communicate through HTTP REST. Shared models, exceptions, and common middleware belong in the shared library. Auth and billing own separate PostgreSQL databases; cross-database joins are prohibited. Redis is ephemeral state only and must not become a system of record. I/O remains asynchronous. Structured logs use `structlog`, domain errors come from the shared exception package, and routing/model/pricing configuration remains externalized in `ai/config/routing.yaml`.

Any change to auth or billing persistence requires an Alembic migration. Any new provider requires an adapter, registry registration, routing catalog entry, contract tests, and pricing/capability metadata. Any new app-store package requires a signed manifest, permission declaration, security review, and rollback path.

## Kickoff sequence

The recommended kickoff sequence is to approve the decision register, create service owners, establish the staging environment, freeze the API/event contract version, and implement one vertical slice: organization login → scoped API key → governed chat request → route decision → provider call → normalized response → usage ledger → user dashboard. The slice should use one real provider and one mock provider, include masking in log-only mode, and pass the full CI and security gates before broader parallel development begins.

## Definition of ready for engineering

A story is ready when its owning service, API/event contract, data ownership, authorization rule, observability fields, migration behavior, test cases, rollout plan, and acceptance criteria are documented. A story that changes a public contract must include a versioning and compatibility decision.

## Definition of done

A story is done when code, tests, migration, documentation, metrics/traces/logs, security review, deployment configuration, rollback behavior, and acceptance evidence are complete. A feature is not done merely because its local UI renders.

## Source references

The authoritative product baseline is the whole-platform BRD delivered with this package. Repository-specific rules are in `AGENTS.md`. Existing implementation and deployment documents remain useful references but may contain legacy examples; when there is a conflict, this handoff package and the current repository guidance take precedence.

## Quality evidence

`quality-report.json` records a deterministic check over all 17 documents. The check passed document presence, author/version/status metadata, comprehensive section structure, and credential-pattern scanning. The supporting directories contain five Mermaid sources, five rendered PNGs, four operational runbooks, and five machine-readable contract examples.
