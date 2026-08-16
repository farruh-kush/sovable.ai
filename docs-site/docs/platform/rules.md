---
title: Platform rules
sidebar_label: Platform rules
---

# Platform rules

These rules define how Solvable is operated and how customer actions are governed.

## Identity and portal boundaries

User Portal registration creates a standard user. Organization Admin registration creates an organization administrator. Agent Creator registration creates an agent-creator identity. Platform Admin identities are provisioned separately and must not be created through public self-registration. A route is not a security boundary; the backend must verify the session role and organization membership on every protected action.

## Routing

Routing applies hard eligibility filters before preference scoring. A provider is ineligible when it is disabled, unhealthy, outside the tenant policy, outside the privacy policy, over budget, or missing required capabilities. Fallbacks are ordered and bounded. Every route decision records the selected model, provider, policy version, reason, latency target, and fallback outcome without storing raw secrets.

## Data protection

Requests are classified before provider dispatch. Masking, tokenization, hashing, blocking, or encryption may be applied according to the organization policy. Raw prompts are not written to ordinary logs. Restoration is permitted only inside the governed request context and only for authorized downstream handling.

## Billing

Usage and payment events are append-only. Amounts are stored as integer minor units in the account currency. Solvable displays Uzbek so'm (`UZS`) as the default customer currency and may present Humo, Uzcard, Visa, and Mastercard as supported payment methods. Live capture is enabled only after a payment provider, signed callbacks, settlement configuration, refunds, and production verification are approved.

## Marketplace

Agents are published only after manifest validation, permission review, security checks, test evidence, and human approval. An organization chooses whether to install an approved agent. Installation does not bypass the organization's data, model, budget, or tool policies.
