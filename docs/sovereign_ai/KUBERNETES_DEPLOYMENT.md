# Standalone Microservices Reference: Kubernetes Deployment

**Author:** Farruh

## Scope

The repository now contains two complementary layers. The existing production-oriented source services remain under `microservices/` and their existing deployment manifests remain under `infrastructure/k8s/`. The tested, self-contained reference implementation is synchronized under `docs/sovereign_ai/microservices_reference/`. Its independent Kubernetes package is under `infrastructure/k8s/standalone-reference/`.

The standalone package deploys five REST services: `gateway`, `auth`, `router`, `provider`, and `billing`. Only `gateway` is exposed through the Ingress. The other services are ClusterIP-only and communicate within the namespace.

## Build and publish

The reference uses one image containing the Python service code. From the repository root:

```bash
docker build -t ghcr.io/YOUR_ORG/ai-routing-reference:0.1.0 \
  docs/sovereign_ai/microservices_reference
docker push ghcr.io/YOUR_ORG/ai-routing-reference:0.1.0
```

Before deployment, replace the placeholder image in `infrastructure/k8s/standalone-reference/deployments.yaml`, or use a Kustomize imageBefore deployment, replace the placeholder image in `infrastructure/k8s/standalone-reference/deployments.yaml`, or use a Kustomize imageBefore deployment, replace the placeholder image in `infrastructure/k8s/standalone-reference/deployments.yaml`, or use a Kustomize imageBefore deployment, replace the placeholder image in `infrastructure/k8s/standalone-reference/deployments.yaml`, or use a Kustomize imageBefore deploymet genBefore deployment, replace the placeholder image in `infrastructure/k8s/standalone-reference/deployments.yaml`, or use a Kustomize imageBefore deployment, replace the placeholder image in `infrastructure/k8s/standalone-reference/deployments.yaml`, or use a  use External Secrets, Vault, a cloud KMS-backed secret manager, or an equivalent institutionally approved mechanism. Do not cBefore deployment, replace the placeholder image in `infrastructure/k8s/stredential.

## Render and validate

```bash
kubectl kustomize infrastructure/k8s/standalone-reference > /tmp/ai-routing-reference.yaml
make reference-k8s-validate
```

The rendered package contains five Deployments, five ClusterIP Services, one routing-policy ConfigMap, one Ingress, three NetworkPolicies, one ServiceAccount, one namespace, one Secret template excluded from the build, and one gateway PodDisruptionBudget.

## Deploy

```bash
kubectl apply -k infrastructure/k8s/standalone-reference
kubectl -n ai-routing-reference rollout status deployment/auth
kubectl -n ai-routing-reference rollout status deployment/router
kubectl -n ai-routing-reference rollout status deployment/provider
kubectl -n ai-routing-reference rollout status deployment/billing
kubectl -n ai-routing-reference rollout status deployment/gateway
kubectl -n ai-routing-reference get pods,svc,ingress
```

The Ingress assumes an NGINX Ingress Controller and a TLS Secret named `gateway-tls`. Replace `ai-routing.example.gov.uz` in `ingress.yaml` with the real domain and provision the certificate through the institution’s approved PKI or certificate manager.

## Runtime behavior

The gateway readiness probe calls `/ready`, which checks all four internal service health endpoints. The router mounts the generated `routing-policy` ConfigMap at `/app/config` and reads the `ROUTING_CONFIG_PATH` environment variable, so policy changes can be rolled out through a controlled ConfigMap update. Provider The gateway readiness probe  this reference. A local Ollama or other provider adapter should be enabled only through an explicit, reviewed overlay and corresponding NetworkPolicy egress rule.

## Security controls in this package

The namespace is labeled for the restricted Pod Security Standard. Pods run as non-root with a RuntimeDefault seccomp profile, Linux capabilities dropped, a read-only root filesystem, and a memory-backed `/tmp`. Internal services are not externally routable. Network policies deny ingress by default, allow same-namespace service traffic and Ingress Controller traffic, and allow DNS plus same-namespace egress. The gateway has a disruption budget of one available replica.

These controls do not replace a production threat model. The reference still uses in-memory auth, billing, and request-local privacy state. Production must replace those components with isolated PostgreSQL databases, Redis for ephemeral state, an encrypted KMS/HSM-backed privacy vault, workload identity or mTLS, durable usage outbox processing, redacted telemetry, image/document inspection, RAG ACL enforcement, and agent tool authorization.

## Rollback and troubleshooting

Use Kubernetes rollout status and history before changing traffic:

```bash
kubectl -n ai-routing-reference rollout history deployment/gateway
kubectl -n ai-routing-reference rollout undo deployment/gateway
kubectl -n ai-routing-reference describe pod -l app.kubernetes.io/name=gateway
kubectl -n ai-routing-reference logs deployment/gateway --all-containers=true
```

If gateway readiness fails, check the four dependency Deployments and their `/health` endpoints first. If a provider call fails, confirm `PROVIDER_MODE`, the provider endpoint, the image version, and the provider egress policy. If routing policy does not change, verify the ConfigMap, `ROUTING_CONFIG_PATH`, and router rollout.
