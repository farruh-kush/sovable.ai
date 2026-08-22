# Kubernetes Deployment Guide

**Author:** Farruh

## Scope

The repository contains two complementary deployment layers. The production-oriented Solvable AI services live under `microservices/`, with deployment manifests under `infrastructure/k8s/`. A self-contained reference implementation lives under `docs/sovereign_ai/microservices_reference/`, with its independent Kubernetes package under `infrastructure/k8s/standalone-reference/`.

The reference package deploys five REST services: `gateway`, `auth`, `router`, `provider`, and `billing`. Only `gateway` is exposed through the Ingress. The remaining services are ClusterIP-only and communicate inside the namespace.

## Build and publish

From the repository root, build and publish the reference image with an immutable version tag:

```bash
docker build -t ghcr.io/YOUR_ORG/ai-routing-reference:0.1.0 \
  docs/sovereign_ai/microservices_reference
docker push ghcr.io/YOUR_ORG/ai-routing-reference:0.1.0
```

Before deployment, replace the placeholder image in `infrastructure/k8s/standalone-reference/deployments.yaml`, or use a Kustomize image transformation. Keep credentials outside Git and inject them through the approved secret manager.

## Render and validate

```bash
kubectl kustomize infrastructure/k8s/standalone-reference > /tmp/ai-routing-reference.yaml
make reference-k8s-validate
```

The rendered package should contain five Deployments, five ClusterIP Services, one routing-policy ConfigMap, one Ingress, three NetworkPolicies, one ServiceAccount, one namespace, one Secret template excluded from the build, and one gateway PodDisruptionBudget.

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

The Ingress assumes an NGINX Ingress Controller and a TLS Secret named `gateway-tls`. Replace `ai-routing.example.gov.uz` in the ingress manifest with the approved domain and provision the certificate through the institution’s certificate manager or PKI.

## Runtime behavior

The gateway readiness probe calls `/ready` and checks the four internal service health endpoints. The router mounts the generated `routing-policy` ConfigMap at `/app/config` and reads `ROUTING_CONFIG_PATH`, allowing policy changes to be rolled out through a controlled ConfigMap update. The reference provider is deterministic and local; an external provider adapter must be enabled only through an explicit reviewed overlay with a corresponding egress policy.

## Security controls

The namespace is labeled for the restricted Pod Security Standard. Pods run as non-root with a RuntimeDefault seccomp profile, dropped Linux capabilities, read-only root filesystems, and a memory-backed `/tmp`. Internal services are not externally routable. NetworkPolicies deny ingress by default while allowing same-namespace service traffic and required DNS and ingress-controller paths.

These controls do not replace a production threat model. Production must replace in-memory identity, billing, and request-local privacy state with isolated PostgreSQL databases, Redis/Valkey for ephemeral state, an encrypted privacy vault, workload identity or mTLS, durable usage outbox processing, redacted telemetry, document inspection, RAG ACL enforcement, and agent tool authorization.

## Rollback and troubleshooting

Use rollout history before changing traffic:

```bash
kubectl -n ai-routing-reference rollout history deployment/gateway
kubectl -n ai-routing-reference rollout undo deployment/gateway
kubectl -n ai-routing-reference rollout status deployment/gateway
```

After rollback, rerun gateway readiness, authenticated smoke requests, routing-policy checks, provider-mock calls, and usage/billing verification. Store rendered manifests, image identifiers, test output, and rollback evidence with the release record.
