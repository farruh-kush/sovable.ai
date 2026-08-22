# Kubernetes Deployment Package

The repository contains a reusable Kustomize base and two cloud overlays. The base deploys the five Python services with the checked-in routing catalog. The Alibaba and AWS overlays replace container registries, patch the public ingress for `api.sovable.ai`, and apply the platform’s network policy.

**Author:** Farruh

## Before applying

Create the `ai-routing` namespace and populate referenced Kubernetes Secrets through the selected cloud secret manager. The committed `secrets.example.env` files contain names and placeholders only; they must never contain credentials. On Alibaba ACK, use KMS, Secrets Manager, or an approved External Secrets controller. On AWS EKS, use AWS Secrets Manager or SSM Parameter Store with External Secrets or the Secrets Store CSI Driver.

Configure PostgreSQL and Redis/Valkey as managed services or approved in-cluster dependencies, then set the `postgres-secret` and `redis-secret` references to private endpoints. Confirm the region, monthly cost cap, image architecture, TLS certificate, DNS, backup, and rollback owner before applying a production overlay.

## Render and validate

Build and push the five images with the immutable registry names and version tag in the chosen overlay. Render the manifests before applying them:

```bash
kubectl kustomize infrastructure/k8s/overlays/alibaba >/tmp/solvable-alibaba.yaml
kubectl apply --dry-run=server -k infrastructure/k8s/overlays/alibaba
```

For AWS, use the same sequence with `infrastructure/k8s/overlays/aws`. Review the rendered output for image tags, secret references, resource requests and limits, probes, NetworkPolicies, ingress/TLS, and non-root security settings. Do not apply a manifest that contains a live secret or a mutable `latest` image tag.

## Alibaba ACK rollout

```bash
kubectl apply -k infrastructure/k8s/overlays/alibaba
kubectl -n ai-routing rollout status deployment/gateway
kubectl -n ai-routing rollout status deployment/auth
kubectl -n ai-routing rollout status deployment/router
kubectl -n ai-routing rollout status deployment/provider
kubectl -n ai-routing rollout status deployment/billing
kubectl -n ai-routing get pods,svc,ingress
```

The ACK cluster must run an image architecture compatible with the build. For the Solvable pilot, publish Linux AMD64 images unless the target node architecture is deliberately changed and verified.

## AWS EKS rollout

```bash
kubectl apply -k infrastructure/k8s/overlays/aws
kubectl -n ai-routing rollout status deployment/gateway
kubectl -n ai-routing get pods,svc,ingress
```

The AWS overlay expects an AWS Load Balancer Controller or equivalent ingress implementation. Confirm the controller, TLS secret, private database endpoints, outbound provider policy, and cost controls before production traffic is enabled.

## Rollback

Use immutable image tags and retain the previous known-good deployment reference:

```bash
kubectl -n ai-routing rollout history deployment/gateway
kubectl -n ai-routing rollout undo deployment/gateway
kubectl -n ai-routing rollout status deployment/gateway
```

Configuration rollback restores the prior routing ConfigMap version. Database rollback uses a forward fix or approved snapshot restore; destructive schema rollback is not assumed. After rollback, rerun health checks, authenticated gateway smoke tests, routing/fallback checks, usage-ledger verification, and dashboard/API checks.

Managed-cloud resources and inference spend are separate from repository validation. No production resource should be created until the cloud, region, monthly cap, deployment approval, and operational owner are recorded.
