# Data Recovery and Restore Validation Runbook

**Author:** Farruh  
**Purpose:** Restore Solvable state after database, storage, event, or cluster failure while protecting billing and tenant isolation.

## 1. Declare scope

Identify whether the incident affects auth, billing, operational metadata, Redis, event delivery, object storage, or the Kubernetes control plane. Freeze risky writes only when necessary. Preserve the incident timeline, backup IDs, database revisions, event offsets, and customer impact.

## 2. Recovery priority

1. Restore secure access to the cluster and secret manager.
2. Restore PostgreSQL auth and billing from the newest verified backup.
3. Validate schema revisions and migration compatibility.
4. Restore object storage metadata/files according to retention and integrity checks.
5. Recreate Redis as ephemeral state and invalidate/rebuild counters and caches.
6. Replay event outboxes or durable event ranges idempotently.
7. Start services in dependency order and run smoke tests.

## 3. PostgreSQL restore

Use the managed database restore mechanism or approved backup tooling. Restore into an isolated instance first, verify checksums, row counts, schema revision, required indexes, tenant references, billing ledger uniqueness, and audit records. Do not point production traffic at an unverified restore.

## 4. Event and billing reconciliation

Replay from the last known durable offset. Consumers must deduplicate by event ID and billing ledger idempotency key. Compare accepted requests, provider attempts, usage events, ledger entries, invoice read models, and reconciliation adjustments. Never “fix” a missing charge by editing a finalized ledger row; emit an adjustment or documented recovery event.

## 5. Redis recovery

Recreate Redis/Valkey with the approved configuration. Expire old rate-limit counters and cache entries. Rebuild provider health windows, policy caches, and budget hot counters from durable state where supported. During rebuild, use conservative limits and route only to approved healthy providers.

## 6. Kubernetes recovery

Restore namespace, service accounts, network policies, secrets references, config, databases, deployments, services, ingress, certificates, and observability in dependency order. Verify image digests and architecture. Do not restore an old manifest containing obsolete credentials or unrestricted access.

## 7. Validation matrix

| Area | Validation |
|---|---|
| Auth | Login, session, membership, key validation, revocation. |
| Billing | Ledger counts, price versions, adjustments, invoice read model. |
| Gateway | Health, models, chat, embeddings, stream, normalized errors. |
| Router | Policy version, provider eligibility, fallback, circuit state. |
| Privacy | Synthetic secret blocked/masked and absent from logs. |
| Events | Outbox/consumer offsets, deduplication, quarantine empty or explained. |
| Data | Dashboard freshness, lineage, export permissions. |
| Security | No old credentials, no public restricted endpoints, audit active. |

## 8. Closeout

Record recovery point and recovery time, backup and restore evidence, data loss or duplication assessment, customer impact, reconciliation result, follow-up controls, and next restore-drill date. A restore is not complete until application smoke tests and billing/privacy checks pass.
