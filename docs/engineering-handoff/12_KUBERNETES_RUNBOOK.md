# Solvable Kubernetes Deployment Runbook

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Scope

This runbook covers local rendering, ACK/EKS deployment, namespaces, secrets, images, databases, Redis, migrations, ingress, TLS, DNS, health verification, rollback, backup, and pilot cleanup. It is a runbook template; production values must be supplied through the environment and secret manager.

## 2. Preconditions

Before deploying, confirm the cloud, region, account/role, approved monthly or pilot cap, cluster context, registry, secret manager, domain ownership, database backup, and on-call owner. Confirm that no credential appears in manifests or shell history.

Minimum platform resources are a Kubernetes cluster, worker capacity sized for gateway, auth, router, provider, billing, dashboard, ingress, cert-manager, PostgreSQL/managed PostgreSQL, Redis/Valkey, registry, and observability. Production should not run PostgreSQL and Redis as unprotected single pods.

## 3. Repository preparation

```bash
# Render and inspect
kubectl kustomize k8s/overlays/alibaba > /tmp/solvable-alibaba.yaml
kubectl apply --dry-run=client -f /tmp/solvable-alibaba.yaml

# Confirm no real credentials appear
rg -n "credential-pattern|secret-pattern|provider-key-pattern" /tmp/solvable-alibaba.yaml

# Confirm images use immutable tags or digests
rg -n "image:" /tmp/solvable-alibaba.yaml
```

The command should report only approved placeholder names or secret references. A real credential is a release blocker.

## 4. Namespace and policy

Use a dedicated namespace such as `ai-routing`. Apply namespace labels, default-deny network policy, resource quotas, limit ranges, service accounts, pod security labels, and workload identities before applications.

```bash
kubectl create namespace ai-routing --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace ai-routing pod-security.kubernetes.io/enforce=baseline --overwrite
kubectl apply -f k8s/standalone-reference/network-policies.yaml
```

Adjust the policy for the actual ingress controller, DNS, secret manager, database, cache, registry, and provider egress paths. Do not blindly apply a policy that prevents DNS or required provider traffic.

## 5. Secrets

Create runtime secrets using the cloud secret manager and External Secrets, Secrets Store CSI Driver, or the approved equivalent. Required keys typically include database URLs, Redis URL, provider API key, Model Studio base URL, gateway admin bootstrap secret, session secret, and registry pull secret if images are private.

```bash
# Example names only; values must come from a secret manager
kubectl -n ai-routing get secret runtime-secrets
kubectl -n ai-routing describe externalsecret runtime-secrets
```

Do not use `kubectl create secret ... --from-literal` in a shared terminal with real values unless the terminal is protected and history is disabled. Prefer cloud-managed references.

## 6. Database and cache

Use separate PostgreSQL databases or schemas according to the service ownership rules. The minimum logical databases are `auth_db` and `billing_db`. Redis/Valkey is ephemeral and must have a defined persistence/failover policy.

Verify connectivity before application deployment:

```bash
kubectl -n ai-routing run db-check --rm -it --restart=Never \
  --image=postgres:16 -- psql "$DATABASE_URL" -c 'select 1'

kubectl -n ai-routing run redis-check --rm -it --restart=Never \
  --image=redis:7 -- redis-cli -u "$REDIS_URL" ping
```

Use temporary diagnostic pods only with sanitized commands. Remove them after verification.

## 7. Images and registry

Push linux/amd64 and, where required, linux/arm64 images with immutable release tags. Confirm the registry manifest and cluster architecture match. For private registries, use a short-lived pull secret or workload identity. For public pilot images, understand that code and dependency contents are publicly pullable.

```bash
kubectl -n ai-routing get deploy -o custom-columns=NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image
kubectl -n ai-routing describe pod <pod-name> | sed -n '/Events:/,$p'
```

## 8. Migrations

Run auth and billing migrations as explicit jobs or controlled release steps. Check current revision, apply migration, verify expected tables and indexes, then deploy services.

```bash
kubectl -n ai-routing apply -f migrations/auth-job.yaml
kubectl -n ai-routing wait --for=condition=complete job/auth-migration --timeout=300s
kubectl -n ai-routing apply -f migrations/billing-job.yaml
kubectl -n ai-routing wait --for=condition=complete job/billing-migration --timeout=300s
```

The actual job manifests must be generated from the release and must reference the exact image and secret version. Never assume a container entrypoint ran a migration unless logs and database state confirm it.

## 9. Application deployment

```bash
kubectl apply -k k8s/overlays/alibaba
kubectl -n ai-routing rollout status deployment/auth --timeout=300s
kubectl -n ai-routing rollout status deployment/billing --timeout=300s
kubectl -n ai-routing rollout status deployment/provider --timeout=300s
kubectl -n ai-routing rollout status deployment/router --timeout=300s
kubectl -n ai-routing rollout status deployment/gateway --timeout=300s
kubectl -n ai-routing rollout status deployment/dashboard --timeout=300s
```

Readiness must include required dependency health, not merely process existence. Liveness must be lightweight and must not restart a pod because a provider is temporarily unavailable.

## 10. Ingress, TLS, and DNS

Install or use the approved ingress controller. Create host rules for `sovable.ai`, `www.sovable.ai` if required, and `api.sovable.ai`. Use cert-manager or a managed certificate service. Validate DNS records before requesting ACME HTTP-01 certificates.

```bash
kubectl -n ingress-nginx get svc
kubectl get ingress -n ai-routing
kubectl get certificate,issuer,order,challenge -n ai-routing
curl -sSIL http://sovable.ai
curl -sSIL https://sovable.ai
curl -sS https://api.sovable.ai/health
```

HTTP should redirect to HTTPS after certificates are valid. Do not expose the database, Redis, Kubernetes API, metrics, or admin-only endpoints publicly.

## 11. Verification matrix

| Check | Command or evidence |
|---|---|
| Nodes | `kubectl get nodes -o wide` |
| Pods | `kubectl get pods -n ai-routing` |
| Events | `kubectl get events -n ai-routing --sort-by=.lastTimestamp` |
| Services | `kubectl get svc -n ai-routing` |
| Ingress | `kubectl get ingress -n ai-routing` |
| Certificates | `kubectl get certificate -n ai-routing` |
| API health | `curl https://api.sovable.ai/health` |
| Dashboard | Browser smoke test at `https://sovable.ai` |
| Models | Authenticated `GET /v1/models` |
| Chat | Authenticated minimal request with a test key |
| Streaming | SSE request ends with `[DONE]` |
| Embeddings | Vector and usage schema check |
| Cache | Repeat request returns policy-approved cache state |
| Billing | Usage row and cost ledger event present |
| Logs | No raw credentials or prompt secrets |
| Metrics | Gateway, provider, router, billing, and node metrics visible |

## 12. Rollback

For an application rollback:

```bash
kubectl -n ai-routing rollout undo deployment/gateway
kubectl -n ai-routing rollout status deployment/gateway --timeout=300s
```

For a bad route or provider configuration, roll back the policy/catalog version without redeploying all services. For a secret issue, disable the provider, rotate the secret, validate, and re-enable. For a schema issue, stop promotion, preserve evidence, and use a forward fix or approved restore procedure.

## 13. Incident commands

```bash
kubectl get nodes
kubectl get pods -A | grep -v Running
kubectl -n ai-routing describe pod <pod>
kubectl -n ai-routing logs deploy/gateway --all-containers --tail=200
kubectl -n ai-routing logs deploy/router --all-containers --tail=200
kubectl -n ai-routing logs deploy/provider --all-containers --tail=200
kubectl -n ai-routing get hpa
kubectl -n ai-routing get pdb
```

Do not paste unredacted logs into public tickets. Use the log-redaction procedure.

## 14. Pilot cleanup

Pilot resources have a 24-hour expiry unless explicitly extended. Cleanup order is: disable public traffic, export required evidence, revoke temporary API keys, rotate provider and registry credentials, delete application workloads, delete ingress/load balancer, delete worker pool, delete cluster, delete registry test repositories, remove DNS records only if they were created for the pilot, and verify billing resources are gone. Keep audit and financial evidence according to policy.

## 15. Production backup and recovery

Document PostgreSQL backup schedule, encryption, retention, restore test frequency, Redis recovery behavior, object-storage versioning, event replay, secret recovery, image retention, and DNS recovery. A backup is not considered valid until a restore test produces an application-usable database.
