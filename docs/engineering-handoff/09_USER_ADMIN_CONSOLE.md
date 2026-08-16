# Solvable User and Admin Console Specification

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Product experience

The console is a light enterprise control plane inspired by modern model studios but differentiated by customer ownership, explicit governance, provider independence, masking controls, route explainability, and usage economics. The User Panel optimizes for safe self-service. The Admin Panel optimizes for platform governance and operational evidence.

The frontend is a statically exported Next.js application served by Nginx. It communicates with the gateway/control-plane APIs and must treat all authorization decisions as server-side. The UI never embeds provider credentials or long-lived private API keys.

## 2. Navigation model

### User Panel

| Area | Screens |
|---|---|
| Overview | Workspace summary, request health, spend, budget status, recent activity. |
| Playground | Chat, embeddings, model selector, route policy, masking preview, streaming, request evidence. |
| API Keys | List metadata, create, rotate, revoke, scopes, expiry, usage hints. |
| Models | Allowed model catalog, capability comparison, price and policy badges. |
| Usage | Requests, tokens, latency, cache, provider/model, cost, export. |
| Billing | Plan, credits, budget, invoices, payment authority, alerts. |
| Team | Members, invitations, roles, projects, service identities. |
| Privacy | Masking policies, test fixtures, provider data policy, retention. |
| Agents and Apps | Catalog, installed apps, permissions, runs, cost, revoke. |
| Security | Sessions, MFA, password, login activity, audit access. |
| Settings | Organization, workspace, project, notifications, API defaults. |

### Admin Panel

| Area | Screens |
|---|---|
| Platform Overview | Availability, traffic, cost, provider health, alerts, active incidents. |
| Organizations | Search, lifecycle, plan, spend, quotas, status, support metadata. |
| Users and RBAC | User search, memberships, roles, MFA state, sessions, access reviews. |
| Providers | Provider registry, endpoints, credentials references, health, circuit state, disable/enable. |
| Models and Pricing | Catalog, capability, aliases, price versions, approval and effective dates. |
| Routing | Policies, simulations, scoring weights, fallbacks, experiments, activation/rollback. |
| Privacy Governance | Global policies, detector versions, provider eligibility, retention defaults. |
| Billing Operations | Ledger health, reconciliation, adjustments, invoice jobs, budgets, spend anomalies. |
| Marketplace Review | Publishers, package scans, manifests, permissions, approvals, suspensions. |
| Observability | Dashboards, traces, logs, SLOs, alerts, release evidence. |
| Audit and Security | Audit search, security findings, incidents, access reviews, evidence exports. |
| System | Feature flags, maintenance, environment metadata, release history. |

## 3. User Panel screen requirements

### Overview

The overview must show current organization/project, selected environment, request count, success rate, p95 latency, token volume, current-period spend, budget threshold, active provider warnings, and recent API-key activity. Each metric has a time range, data freshness marker, and drill-down link. Empty state explains how to create a project and key.

### Playground

The Playground supports chat and embeddings. It includes model selection filtered by server policy, route-policy selection, masking preview, stream toggle, temperature and token controls, request ID, response timing, token usage, cache state, route class, and copyable code examples. The default playground uses a safe test key or a server-side session, not a secret pasted into browser storage.

The screen must clearly distinguish “simulation” from “real provider call.” A simulation displays candidate filtering and expected cost without upstream invocation. A real call displays provider evidence only according to the organization privacy policy.

### API Keys

The key list shows name, prefix, scopes, project, status, created, expiry, last used, and actions. Create flow includes name, project, scopes, model/provider restrictions, expiry, IP restrictions if enabled, rate limit, and budget. The success screen has a one-time secret warning and copy/download action without ever exposing it again.

### Usage and Billing

Charts and tables support time range, project, key, model, provider, status, and grouping. The UI labels estimated versus finalized costs and shows cached tokens separately. Billing screens must not imply a final invoice when reconciliation is pending.

### Team and Security

Team flows show invitations, roles, pending states, last activity, and access review. Security shows active sessions, sign-in events, MFA enrollment, recovery codes, password reset, and key rotation. High-risk actions require reauthentication or MFA according to policy.

## 4. Admin Panel screen requirements

Admins need searchable tables with server-side pagination, filters, sort allowlists, bulk actions with confirmation, audit linkage, and export jobs. Provider screens include health timeline, latency/error distributions, recent failures, circuit state, credential reference and rotation date, model list, data policy, and disablement action.

Routing screens show active policy version, draft versions, hard filters, weighted preferences, candidate simulation, fallback chain, recent route-decision samples, and rollback. Activation requires a policy diff, simulation result, approver, effective time, and rollback target.

The audit screen provides read-only evidence with filters for actor, action, tenant, target, request ID, outcome, and time. Raw prompt content is not displayed by default. Any privileged content access must be an explicit audited break-glass flow.

## 5. Permission matrix

| Capability | Viewer | Developer | Org Admin | Billing Admin | Org Owner | Platform Support | Platform Admin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Read project metadata | Yes | Yes | Yes | Yes | Yes | Support scope | Platform scope |
| Create API key | No | Yes | Yes | No | Yes | No | No |
| Revoke API key | No | Own/project | Project | No | Org | No | Break-glass only |
| Read usage | Limited | Project | Org | Org | Org | Support scope | Platform aggregate |
| Change budgets | No | No | No | Yes | Yes | No | Global policy |
| Invite members | No | No | Yes | No | Yes | No | No |
| Change org roles | No | No | Yes | No | Yes | No | No |
| Activate route policy | No | Draft only | Review | No | Yes | No | Global |
| Register provider | No | No | No | No | No | No | Yes |
| Disable provider | No | No | No | No | No | Incident assist | Yes |
| Approve marketplace app | No | No | No | No | No | Review | Yes |
| View raw content | No | Policy-limited | Policy-limited | No | Policy-limited | No by default | Break-glass |
| Read audit | Own actions | Project | Org | Billing scope | Org | Support scope | Platform |

This matrix is a product baseline. Effective permissions are computed by the authorization service and may be narrowed by resource policy.

## 6. Frontend state requirements

Every data-driven screen must handle loading, empty, success, stale, permission denied, unauthenticated, validation error, rate limit, dependency unavailable, partial data, and unexpected error states. Actions must show pending, success, retryable failure, and irreversible confirmation states.

| State | UI behavior |
|---|---|
| Loading | Skeleton or progress state; preserve navigation context. |
| Empty | Explain why empty and provide a safe next action. |
| Stale | Show last updated timestamp and refresh action. |
| Forbidden | Explain insufficient permission without revealing hidden resource existence. |
| Rate limited | Show retry timing and do not duplicate mutation. |
| Offline/dependency failure | Preserve entered form data where safe and offer retry. |
| Mutation pending | Disable duplicate submit; use idempotency key. |
| Secret created | Show once-only secret screen and explicit storage warning. |
| Destructive action | Require typed confirmation or reauthentication as configured. |
| Partial dashboard | Show available cards and identify unavailable sources. |

## 7. Accessibility and responsive behavior

The console must provide keyboard navigation, visible focus, semantic labels, accessible error association, sufficient contrast, non-color-only status, reduced-motion support, and screen-reader-friendly tables. Responsive layouts must work on desktop and tablet; mobile should support monitoring and key administrative actions without exposing secrets in unsafe contexts.

## 8. Frontend architecture rules

Server state uses a typed API client generated from the contract or maintained as a strict client package. API errors map to user-safe messages while preserving request IDs for support. Query keys include organization, project, filters, and policy context to prevent cross-tenant cache leakage. Sensitive fields are cleared from client state after use.

## 9. Acceptance criteria

A user cannot see another organization’s project, key, usage, invoice, app installation, or audit event. A role change updates navigation and server authorization. Playground requests honor model, route, masking, budget, and stream policies. Admin disablement changes routing eligibility. Every privileged action produces an audit link visible to authorized users.
