# Solvable Identity, RBAC, Quotas, and Billing Specification

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Scope

This document defines the organization-aware identity and commercial control plane: registration, sessions, organizations, workspaces, projects, members, roles, API keys, quotas, budgets, pricing, usage, credits, invoices, and audit. It is the source of truth for User Panel and Admin Panel behavior.

## 2. Hierarchy

```text
User -> Organization -> Workspace -> Project -> API Key / Service Identity
```

A user may belong to multiple organizations. A workspace belongs to exactly one organization. A project belongs to exactly one workspace. API keys are project-scoped. Platform administrators are not organization members by default; their access is an explicit platform role with stronger audit and MFA requirements.

## 3. Roles

| Role | Scope | Core permissions |
|---|---|---|
| `platform_admin` | Platform | Manage providers, global catalog, security policy, platform users, incidents, and marketplace review. Cannot read customer content by default. |
| `platform_support` | Platform | Read operational metadata and assist with support; no secret retrieval, billing mutation, or raw content access. |
| `org_owner` | Organization | Manage organization, billing authority, members, projects, policy, provider enablement, and data governance. |
| `org_admin` | Organization | Manage members, projects, policy drafts, and operational settings; billing mutation only if granted. |
| `billing_admin` | Organization | Manage plan, budgets, credits, invoices, payment settings, and exports. |
| `developer` | Project | Create/use scoped API keys, test models, view project usage, and manage project route drafts. |
| `analyst` | Project | Read usage, route evidence, dashboards, and permitted audit metadata. |
| `viewer` | Organization/project | Read limited non-sensitive metadata. |
| `agent_operator` | Project | Install/run approved agents and view run evidence within project policy. |
| `service_identity` | Project | Machine-to-machine API access through explicit scopes; no console login. |

RBAC is deny-by-default. A permission check evaluates role, organization membership, project scope, resource ownership, policy state, and environment. UI hiding is not a security control.

## 4. Authentication

The initial product supports email/password plus secure session management. The target supports OIDC/SSO for enterprise organizations, MFA for privileged actions, recovery codes, session revocation, device visibility, suspicious-login detection, and optional passwordless enrollment.

Passwords are salted and hashed with a current memory-hard algorithm. Sessions use secure, HttpOnly, SameSite cookies with short-lived access and rotating refresh behavior. Login, password reset, MFA, invitation, and key operations are audited. Rate limits and account lockout policies must resist credential stuffing without creating an easy denial-of-service vector.

## 5. API-key lifecycle

A key has a name, project, owner, scopes, model allowlist, provider allowlist, IP/referrer allowlist where applicable, rate limit, budget, creation time, expiry, last-used metadata, status, and secret hash. The secret is shown once. Rotation creates a replacement and may overlap validity for a short controlled period. Revocation is immediate at the source of truth and cache invalidation is emitted.

Recommended scopes include:

```text
chat:write
embeddings:write
models:read
usage:read
routes:simulate
agents:run
files:read
files:write
billing:read
admin:read
admin:write
```

Keys must never receive organization-wide admin permissions by default. Browser applications should use a backend relay or ephemeral scoped token, not a long-lived private API key.

## 6. Quotas and rate limits

Limits apply at organization, workspace, project, user, key, provider, model, and IP scopes. The effective limit is the most restrictive applicable value. Redis counters implement the hot path; a durable usage stream reconciles actual usage.

| Limit | Example |
|---|---|
| Requests per minute | 60 per key, 600 per project. |
| Concurrent streams | 5 per key, 50 per project. |
| Tokens per minute | Model/provider-specific. |
| Monthly token quota | Plan and project-specific. |
| Monthly spend | Hard stop or alert-only. |
| Max request body | 1 MiB baseline, policy-configurable. |
| Max stream duration | 5 minutes baseline. |
| Max agent run | 120 seconds baseline. |

A hard budget stop must happen before provider invocation where estimated cost is available. After usage is measured, the ledger reconciles the estimate.

## 7. Pricing and billing

Billing distinguishes:

1. upstream provider cost;
2. Solvable platform charge;
3. markup or subscription allocation;
4. credits, discounts, and adjustments;
5. taxes or external payment-provider charges.

Every finalized usage record stores the price version used. A price change creates a new version with effective time; historical usage never changes retroactively. Estimated usage is labeled until provider-reported usage or a reconciliation rule finalizes it.

## 8. Budget behavior

Budget policies define period, scope, currency, limit, alert thresholds, grace behavior, and hard-stop behavior. Alerts are emitted at configurable thresholds. Hard stops prevent new upstream requests while allowing read-only console access and graceful completion of already accepted requests.

A budget owner can set a lower project limit than the organization. A lower-level budget cannot raise an organization hard stop. Budget changes require permission and audit evidence.

## 9. Invoice and export behavior

Invoices are read models generated from finalized ledger events and adjustments. Exports are asynchronous jobs with signed, expiring download URLs. Sensitive line-item fields are filtered by role. Reconciliation compares provider receipts or reported usage with the internal ledger and produces adjustment events rather than mutating history.

## 10. Audit requirements

Audit events include actor, organization, project, action, target, decision, before/after metadata where safe, request ID, IP/device metadata according to policy, and timestamp. Secrets, raw passwords, provider keys, and raw prompt content are excluded. Audit data is append-only and access is itself audited.

## 11. Acceptance criteria

The system must prove that a revoked key is rejected, a cross-project key is rejected, an expired key is rejected, insufficient scopes are rejected, a member cannot exceed role permissions, a budget hard stop blocks new provider calls, a provider price change preserves historical charge, a rotation overlap behaves as configured, and usage appears in the correct organization/project read model without cross-tenant leakage.
