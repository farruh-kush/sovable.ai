---
title: Billing and payments
sidebar_label: Billing
---

# Billing and payments

Solvable uses Uzbek so'm (`UZS`) as the default display and ledger currency. Customer invoices show the plan, usage, markup, discounts, taxes or required metadata, payment state, and any refund or adjustment.

## Payment methods

The payment abstraction supports Humo, Uzcard, Visa, and Mastercard. The actual checkout is delegated to a contracted acquiring provider. Supported methods may be shown in the UI while the provider remains in a pending configuration state.

## Payment lifecycle

A payment moves from draft to pending, authorization, capture, refund, or failure. Provider callbacks are verified, idempotent, and reconciled against invoice ID, amount, currency, and provider event ID. Browser redirects alone never prove a successful capture.

## Budgets

Organization Admin sets monthly caps, per-key limits, alert thresholds, and model eligibility. A budget guard can block new requests before a provider call. Usage and billing events remain append-only so a later reconciliation does not rewrite history.

## Provider activation

Live capture requires merchant credentials, callback signing, settlement configuration, refund support, compliance review, and production test evidence. Until those prerequisites are approved, the portal must show a clear configuration state and must not claim that funds were captured.
