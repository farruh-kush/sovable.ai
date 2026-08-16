---
title: Platform Admin guide
sidebar_label: Platform Admin
---

# Platform Admin guide

Platform Admin is the isolated operator surface for the Solvable platform. It is entered through `https://sovable.ai/controller` and is not available through public self-registration.

## Provider operations

Platform Admin manages provider adapters, capability catalogs, secret references, health status, retry policy, circuit breakers, failover eligibility, and emergency disablement. Secret values remain in a managed secret store and are never displayed in the portal.

## Routing and model policy

Configure static mappings, cost and latency preferences, quality rules, region constraints, privacy eligibility, fallback chains, and budget controls. Each change creates a versioned policy and an audit event. Test a policy against representative fixtures before activating it globally.

## Pricing and billing operations

Maintain model input/output prices, markup rules, customer plan limits, payment-provider settings, invoice configuration, refund policy, and settlement exports. UZS prices are stored as integer tiyin values and reconciled against append-only payment events.

## Security and observability

Review authentication events, key activity, anomalous requests, provider failures, latency SLOs, cost signals, and marketplace review findings. Emergency controls such as disabling a provider or revoking a package require a reason and produce incident evidence.
