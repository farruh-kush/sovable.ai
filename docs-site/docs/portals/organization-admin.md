---
title: Organization Admin guide
sidebar_label: Organization Admin
---

# Organization Admin guide

Organization Admin is the customer control surface for a tenant. Register at `https://sovable.ai/admin/register` when you are creating or administering an organization.

## Organization boundary

The organization is the boundary for members, API keys, budgets, data policy, enabled models, installed agents, and billing. Organization Admin can invite members and assign least-privilege roles such as builder or viewer. Role changes and invitations are audit events.

## Budgets and billing

Set monthly spend caps, alert thresholds, model eligibility, and per-key limits. The billing view uses Uzbek so'm (`UZS`) as the default display currency and presents Humo, Uzcard, Visa, and Mastercard as customer payment methods when a provider is configured. A payment method may be visible as supported while the provider remains pending merchant credentials.

## Data policy

Define classifications, masking transformations, retention, provider eligibility, and restoration rules. Policy changes should be reviewed by the organization owner and are applied to subsequent requests according to the policy version.

## Agents

Organization Admin reviews an agent's permissions, data sources, model policy, side effects, price, publisher, and release before installing it. Installation is tenant-scoped and can be disabled without deleting the publisher's marketplace listing.
