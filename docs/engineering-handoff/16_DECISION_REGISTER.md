# Solvable Architecture and Product Decision Register

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. How to use this register

This register captures decisions that constrain implementation. Accepted decisions should not be reopened casually; an amendment requires a new record, rationale, impact analysis, and owner. Open decisions have a proposed default so teams can proceed without blocking, but the responsible owner must confirm before production enforcement.

## 2. Accepted decisions

| ID | Decision | Rationale | Consequence |
|---|---|---|---|
| ADR-001 | Use a unified OpenAI-compatible public API baseline. | Lowers client migration cost and creates a stable contract. | Provider-specific features require namespaced extensions. |
| ADR-002 | Use modular provider adapters. | Isolates provider inconsistency and supports replacement. | Adapter contracts and contract tests are mandatory. |
| ADR-003 | Separate auth and billing database ownership. | Prevents cross-domain joins and limits blast radius. | Read models/events are required for cross-domain views. |
| ADR-004 | Use event-driven asynchronous propagation. | Supports decoupling, analytics, audit, and reconciliation. | Idempotency, schema registry, and replay are required. |
| ADR-005 | Do not log raw prompts/responses by default. | Protects customer confidentiality and reduces breach impact. | Debugging uses request IDs, metadata, sanitized fixtures, and break-glass controls. |
| ADR-006 | Billing ledger is append-only. | Preserves financial auditability. | Corrections are adjustment events, not updates/deletes. |
| ADR-007 | Redis is ephemeral. | Avoids using cache as financial or identity source of truth. | Durable DB/events must back every important state change. |
| ADR-008 | Deterministic hard filters precede route scoring. | Prevents preference logic from bypassing security or compliance. | Every route decision stores policy and exclusion reasons. |
| ADR-009 | Kubernetes is the deployment target. | Provides modular rollout, resource isolation, and cloud portability. | Helm/Kustomize, probes, policies, and rollback are required. |
| ADR-010 | Alibaba ACK is the current pilot environment. | Matches approved pilot access and Singapore region needs. | AWS overlay remains portable but is not the current production path. |
| ADR-011 | Free-quota-only mode is the pilot default. | Controls inference spend while validating platform behavior. | Requests must respect provider quota and budget hard stops. |
| ADR-012 | Model and provider catalog are versioned. | Pricing, capability, and governance change over time. | Historical route and billing records reference versions. |
| ADR-013 | Marketplace packages require signed manifests. | Enables permission review and supply-chain provenance. | App installation depends on scans, signatures, and policy approval. |
| ADR-014 | Agent runtime is isolated from core services. | Limits package and prompt-injection blast radius. | Runtime needs brokered tools, egress control, and resource limits. |
| ADR-015 | Figma is the intended product design source. | Aligns User/Admin Panel work with a shared design system. | Engineering needs export/inspection handoff before implementation. |

## 3. Proposed defaults requiring confirmation

| ID | Decision | Proposed default | Owner | Due |
|---|---|---|---|---|
| DEC-001 | Public registration | Invite-first for production; self-serve trial with email verification in controlled beta. | Product + Security | Before beta |
| DEC-002 | MFA requirement | Required for platform admins, org owners, billing admins, and break-glass; optional for developers initially. | Security | Before beta |
| DEC-003 | Organization model | One user may belong to many organizations; project keys remain single-project. | Product + Identity | Before User Panel GA |
| DEC-004 | Default retention | Metadata-only requests; raw content disabled; short TTL for transformed/tokenized content. | Privacy + Legal | Before customer data |
| DEC-005 | Provider approval | Platform admin approval plus data-policy review, capability test, pricing metadata, and credential health check. | Provider Platform + Security | Before second provider |
| DEC-006 | Billing activation | Start with usage ledger and hard budget; enable paid invoices only after reconciliation and payment controls are verified. | Billing | Before paid beta |
| DEC-007 | Customer content access | No support access by default; time-bound break-glass with customer approval where feasible. | Security + Support | Before support launch |
| DEC-008 | Agent side effects | Read-only agents first; all external communication, financial, and destructive actions require approval. | Ecosystem + Security | Before marketplace beta |
| DEC-009 | Data warehouse | Begin with managed PostgreSQL/object storage exports; adopt dedicated warehouse when volume and query isolation require it. | Data Platform | 90-day review |
| DEC-010 | Adaptive routing | Keep disabled until offline evaluation, stop conditions, and cost controls are approved. | Routing Intelligence | P2 gate |

## 4. Decision consequences

Teams must record when an implementation intentionally diverges from this register. A divergence without an updated decision creates hidden architecture and operational risk. Product, security, and finance owners should review the register monthly during the pilot and before each major release.
