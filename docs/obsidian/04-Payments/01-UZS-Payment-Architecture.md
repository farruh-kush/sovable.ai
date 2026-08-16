# Uzbek So'm Payment Architecture

Author: Farruh

## Product decision

Solvable uses Uzbek so'm (`UZS`) as the default billing currency. The internal ledger stores integer tiyin values to avoid floating-point errors. The interface displays human-readable amounts such as `149 000 so'm` and identifies the payment method selected by the customer.

## Supported payment methods

| Method | Internal code | Product meaning | Activation requirement |
|---|---|---|---|
| Humo | `humo` | Domestic Uzbek card rail | Contracted acquiring provider and merchant credentials |
| Uzcard | `uzcard` | Domestic Uzbek card rail | Contracted acquiring provider and merchant credentials |
| Visa | `visa` | International card rail | Acquirer support and settlement configuration |
| Mastercard | `mastercard` | International card rail | Acquirer support and settlement configuration |

A unified acquirer such as ATMOS or Octobank is a candidate implementation route because both publicly describe support for Humo, Uzcard, Visa, and Mastercard. The final provider must be selected after merchant onboarding, commercial review, PCI/compliance review, callback documentation, and settlement-account confirmation.

## Payment states

The payment state machine is `draft → pending → redirect_required → authorized → captured`. Failure paths include `failed`, `cancelled`, `refunded`, and `partially_refunded`. A payment cannot be marked captured from a browser callback alone; the server must verify the signed provider callback and reconcile provider event ID, invoice ID, amount, currency, and organization.

## Webhook rules

Callbacks are accepted only over HTTPS and only after signature verification. Each provider event ID is idempotent. Replayed events must return a safe acknowledgement without duplicating ledger entries. Amount and currency mismatches are rejected and alerted. The append-only payment event stores provider, method, invoice, amount in tiyin, currency, event ID, state transition, received time, signature result, and reconciliation result.

## Refunds and disputes

Full and partial refunds create new ledger events and do not mutate the original capture. The user-facing invoice shows the original payment, refund amount, remaining captured amount, and current state. Organization Admin can request a refund according to policy; Platform Admin can reconcile or override only with a reason and audit record.

## Activation gate

The current product may display supported methods and a payment-provider configuration state, but it must not capture live funds while merchant credentials, signed callback secrets, settlement data, refund rules, fiscal-receipt requirements, and production test evidence are missing. A provider adapter becomes active only after a configuration checklist is approved by Platform Admin.

## Reference sources

- [ATMOS single payment window](https://atmos.uz/en/blog/single-payment-window)
- [GlobalPay payment infrastructure](https://globalpay.uz/en)
- [Octobank Internet Acquiring](https://octobank.uz/en/press-center/kak-biznesu-prinimat-oplatu-onlayn-s-internet-ekvayringom-ot-octobank)
