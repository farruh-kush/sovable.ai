# Solvable Kubernetes deployment

The repository contains a reusable Kustomize base and two cloud overlays. The base deploys the five Python services with the checked-in routing catalog; the Alibaba and AWS overlays replace container registries, patch the public ingress for `api.solvable.ai`, and add a gateway egress policy.

## Before applying

Create the `ai-routing` namespace and populate the referenced Kubernetes Secrets through the selected cloud secret manager. The committed `secrets.example.env` files are names only and contain no credentials. On Alibaba ACK, use KMS/Secrets Manager or an External Secrets controller. On AWS EKS, use AWS Secrets Manager/SSM Parameter Store with External Secrets or the Secrets Store CSI Driver. Configure PostgreSQL and Redis/Valkey as managed services, then set the `postgres-secret` and `redis-secret` values to their private endpoints.

Build and push the five images with the registry names in the chosen overlay, replace the placeholder version tag, configure TLS, and render before applying:

```bash
kubectl kustomize k8s/overlays/alibaba >/tmp/solvable-alibaba.yaml
kubectl apply --dry-run=server -k k8s/overlays/alibaba
kubectl apply -k k8s/overlays/alibaba
kubectl -n ai-routing rollout status deployment/gateway
```

For AWS, use the same sequence with `k8s/overlays/aws`. The AWS overlay expects the AWS Load BalFor AWS, use the same sequence with `k8s/overlays/aws`. The AWS overlay expects the AWS Load BalFor AWS, use the same sequence with `k8s/overlays/aws`. The AWS overlay expects the AWS Load BalFor AWS, use the same sequence with `k8s/overlays/aws`. The AWS overlay expects the AWS Load BalFor AWS, use the same sequence with `k8s/overlays/aws`. The AWS overlay expects the AWS Load BalFor AWS, use the same sequence with `k8s/overlays/aws`. The AWS overlay expects the AWS Load BalFor AWS, use the same sequence with `k8s/overlays/aws`. . These are managed-cloud choices and are priced separately in [`docs/DEPLOYMENT_COST_ESTIMATE.md`](../docs/DEPLOYMENT_COST_ESTIMATE.md). No production cloud resource should be created until the cloud, region, monthly cap, and deployment approval are confirmed.
