# Solvable DevOps, CI/CD, and Environment Guide

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Environment model

| Environment | Purpose | Data | Providers | Deployment rule |
|---|---|---|---|---|
| Local | Fast developer feedback and contract tests. | Synthetic/local only. | Mock by default; optional sandbox provider. | Docker Compose or local Kubernetes. |
| CI | Repeatable tests, scans, builds, contract validation. | Ephemeral fixtures. | Mocked upstreams; no production keys. | Every pull request. |
| Development | Shared integration and UI development. | Synthetic or sanitized. | Test provider credentials with hard caps. | Automatic after protected branch checks. |
| Staging | Production-like release verification. | Sanitized fixtures; no raw customer data. | Staging provider accounts with budgets. | Approval after full checks. |
| Production | Customer workloads. | Customer-controlled by policy. | Approved providers and secret manager. | Explicit release approval and rollback plan. |

Every environment has separate databases, Redis, credentials, registry tags, domains, encryption keys, and observability namespaces. Production credentials must never be available to local or CI jobs.

## 2. Repository workflow

Use protected branches and pull requests. A change must identify the affected service, contract, migration, security impact, test evidence, and rollout/rollback behavior. Provider and pricing changes require catalog review. Auth and billing schema changes require Alembic migration review. Kubernetes changes require rendered-manifest and policy checks.

Recommended branches are `main` for production-ready code, `develop` only if the team chooses a long-lived integration branch, and short-lived feature branches. Tags use `service-vMAJOR.MINOR.PATCH` or an organization-wide release identifier. Image tags must be immutable release tags; `latest` is prohibited in deployments.

## 3. CI pipeline

```mermaid
flowchart LR
    PR[Pull Request] --> Format[Format and Type Check]
    Format --> Unit[Unit Tests]
    Unit --> Contract[API and Adapter Contract Tests]
    Contract --> Security[Secret, Dependency, SAST, SBOM, Image Policy]
    Security --> Build[Build linux/amd64 and linux/arm64 Images]
    Build --> Render[Render and Validate Kubernetes]
    Render --> Integration[Ephemeral Integration Tests]
    Integration --> Review[Required Review]
    Review --> Merge[Merge Protected Branch]
    Merge --> Publish[Publish Signed Images and Artifacts]
    Publish --> DeployStaging[Deploy Staging]
    DeployStaging --> Smoke[Smoke, Load, and Security Tests]
    Smoke --> Approve[Production Approval]
    Approve --> DeployProd[Progressive Production Deployment]
```

## 4. Required CI stages

| Stage | Required checks |
|---|---|
| Formatting | Ruff/Black or project-equivalent Python formatting; TypeScript/Prettier checks. |
| Static typing | Python type checks and frontend TypeScript strict checks. |
| Unit | Service-local tests with async fixtures. |
| Contract | Public OpenAPI, internal service contracts, provider adapter contracts, event schema checks. |
| Security | Secret scan, dependency vulnerability scan, container scan, SBOM, license policy, IaC/Kubernetes policy. |
| Build | Reproducible multi-architecture images; no secrets in layers; non-root where possible. |
| Manifest | Kustomize render, schema validation, policy validation, image tag check, resource and secret reference check. |
| Integration | PostgreSQL, Redis, service startup, migration, gateway request, provider mock, billing event. |
| Browser | Auth, User Panel, Admin Panel permissions, Playground, responsive and accessibility smoke tests. |
| Release | Signed artifacts, changelog, migration plan, rollback image references, owner approval. |

## 5. Image strategy

Build images from the repository root with explicit production Dockerfiles and a target architecture. Publish immutable digest-pinned images to ACR/ECR or another approved registry. The image must include build metadata: service, version, commit, build timestamp, and schema compatibility version.

The release process must verify that the image architecture matches the cluster nodes. The prior pilot exposed an ARM/x86 mismatch, so architecture verification is a required release gate.

## 6. Secrets management

Secrets are created in a cloud secret manager or Kubernetes secret integration. The repository may contain only names, examples, or references with placeholder values. Secret values must not appear in Git, Docker build context, image layers, logs, CI output, screenshots, or browser bundles.

Required secret classes include database URLs, Redis credentials, provider keys, signing keys, session secrets, webhook secrets, registry credentials, encryption keys, and third-party connector credentials. Each secret has an owner, rotation interval, emergency rotation procedure, last-used metadata, and environment scope.

## 7. Database and migration deployment

Migrations are separate release artifacts and must be reviewed. The deployment process is:

1. Verify database backup and migration compatibility.
2. Apply additive migration.
3. Deploy application version compatible with old and new schema.
4. Backfill asynchronously with progress and resume state.
5. Switch reads/writes after validation.
6. Remove obsolete columns or indexes only in a later release.

Never run a destructive migration automatically during a normal pod startup. A migration job must have a bounded timeout, clear owner, log access, and rollback or restore procedure.

## 8. Progressive delivery

For production, use rolling deployments with readiness gates at minimum. For higher-risk gateway, router, provider, billing, and privacy releases, use blue/green or canary traffic when the platform supports it. Verify request success, latency, error class, provider attempts, usage ledger, and privacy evidence before promotion.

## 9. Rollback

Application rollback uses immutable image references and `kubectl rollout undo` or a release controller. Config rollback restores the previous policy/catalog version. Database rollback uses forward-fix or snapshot restore; destructive schema rollback is not assumed. Provider rollback can disable a provider and activate the last valid route policy without redeploying the entire platform.

## 10. Cost controls

Every environment has resource quotas, max replicas, budget alerts, provider spend limits, and expiry labels for temporary resources. Pilot clusters, trial resources, test keys, registries, load balancers, and public endpoints receive an owner and cleanup deadline. A release that creates a new paid resource must include a cost estimate and an approval record.

## 11. Developer local workflow

```bash
# Start local dependencies
cp .env.example .env.local
make up

# Run service tests
./scripts/run_tests.sh

# Render the selected Kubernetes overlay
kubectl kustomize k8s/overlays/alibaba > /tmp/solvable-alibaba.yaml

# Run the dashboard checks
cd web/dashboard && npm run typecheck && npm run build
```

The exact commands must remain synchronized with the repository Makefile and service READMEs. Developers must not use production endpoints or keys in local `.env` files.

## 12. Release checklist

Before production deployment, confirm tests, image digest, architecture, migration plan, secret references, health probes, resource requests/limits, network policies, ingress/TLS, DNS, provider health, budgets, dashboards, alerts, rollback, backup, and on-call owner. Store evidence with the release record.
