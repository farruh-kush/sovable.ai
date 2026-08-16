# Solvable Release Workflow

Author: Farruh

## Delivery rule

Every release is a vertical slice that can be tested and rolled back. The source repository, static dashboard output, container image, Kubernetes manifest, live domain, and Obsidian notes must describe the same release. A Figma frame may guide the experience, but a screen is not considered delivered until its route, state behavior, and authorization boundary are tested.

## Sequence

| Stage | Check | Evidence |
|---|---|---|
| Product | Portal scope and acceptance criteria approved | Issue or decision note |
| Design | Figma frame or local design plan aligned | Frame link or vault note |
| Code | Frontend/backend implementation complete | Commit and diff check |
| Validation | Build, tests, security scan, route smoke tests | CI run and test report |
| Image | Linux/amd64 immutable image published | Registry digest |
| Deploy | ACK rollout and readiness | Deployment status |
| Live | Public route, API, auth, payment-disabled state verified | HTTPS smoke evidence |
| Archive | Obsidian note and release record updated | Release note |

## Four-portal acceptance gate

A release is ready when `/controller`, `/admin`, `/portal`, and `/creator` have working entry pages; each protected action returns the correct role boundary; User and Agent Creator registrations do not create organization-admin identities; Platform Admin has no public self-registration; and the public landing page links to all four portals.

## Payment acceptance gate

UZS billing screens may be deployed with `credentials required` status. Live capture requires a provider adapter, callback signature verification, idempotency tests, refund tests, settlement configuration, and a production test payment. Until that gate passes, the payment UI must never claim that a transaction was captured.

## Rollback

Rollback uses the previous immutable dashboard and service image tags. Database migrations are forward-compatible and never rolled back destructively during an incident. Payment events and billing ledger entries are append-only. Portal route changes are verified after rollback so authentication and public navigation remain available.
