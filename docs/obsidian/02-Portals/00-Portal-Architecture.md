# Four-Portal Architecture

Author: Farruh

## Purpose

The Solvable product has four explicit entry points. Each portal communicates the same customer-controlled AI infrastructure promise but exposes only the responsibilities appropriate to its role.

| Portal | Route family | Identity role | Registration rule | Sensitive boundary |
|---|---|---|---|---|
| Platform Admin | `/controller` | `platform_controller` | Invite or managed provisioning only | Provider secrets, platform policy, deployments, global audit |
| Organization Admin | `/admin` | `org_admin` | Email or phone verification with organization-admin context | Tenant members, quotas, billing configuration, organization policy |
| User | `/portal` and `/dashboard` | `user` | Open registration with email or phone verification | Personal workspace, API keys, playground, usage, installed agents |
| Agent Creator | `/creator` | `agent_creator` | Creator registration with review and payout-profile onboarding | Agent packages, tool scopes, versions, tests, review, settlement records |

## Authentication and authorization

The route alone is not an authorization boundary. Every portal request must carry a first-party session or a scoped API key, and the backend must verify the role and organization membership before returning data. A user who manually enters `/admin` must receive an authorization response and a safe redirect, not an organization-admin view. Platform Admin must not be created through normal public registration.

The `account_type` context is persisted on verification challenges so that a code requested for a User Portal or Agent Creator flow cannot be silently replayed into another registration context. Successful registration maps to `user`, `org_admin`, or `agent_creator`. Platform-controller identities are provisioned separately and should require stronger authentication and step-up verification.

## Shared navigation

The public landing page presents four cards or actions in this order: User Portal, Organization Admin, Agent Creator, and Platform Admin. The visual hierarchy makes User Portal the default product entry, Organization Admin the customer-control entry, Agent Creator the marketplace-publisher entry, and Platform Admin the restricted operations entry.

Inside the application shell, the User Portal shows workspace and account functions. Organization Admin shows members, policy, billing, providers enabled for the tenant, and installed agents. Agent Creator shows marketplace, Creator Studio, review pipeline, releases, and settlements. Platform Admin shows providers, routing, models, pricing, tenant governance, security, observability, and audit.

## Workflow boundaries

A creator can draft and submit an agent but cannot publish directly. A reviewer or Platform Admin approves the package after automated manifest, permissions, security, and quality checks. An Organization Admin installs an approved agent for a tenant. A User can run an installed agent only within the tenant policy and their own permission scope.

An Organization Admin can configure a budget but cannot alter global provider credentials or global routing policy. Platform Admin can disable a provider globally, but the action must be audited and must preserve customer-visible incident evidence. Billing events are append-only and reconciled independently of presentation screens.
