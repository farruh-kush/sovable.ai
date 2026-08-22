# Solvable Kubernetes deployment

**Author:** Farruh

This directory contains the reusable Kustomize base and cloud overlays for the five production microservices. The Alibaba ACK and AWS EKS overlays select registries, ingress, TLS, security policy, and cloud-specific settings without changing service code.

## Before applying

Populate Kubernetes Secrets through the selected cloud secret manager. The committed secret templates contain names only and no credentials. Configure PostgreSQL and Redis/Valkey through approved managed or protected services, then validate the generated manifests before applying them.

For Alibaba ACK:

```bash
kubectl kustomize infrastructure/k8s/overlays/alibaba >/tmp/solvable-alibaba.yaml
kubectl apply --dry-run=server -k infrastructure/k8s/overlays/alibaba
kubectl apply -k infrastructure/k8s/overlays/alibaba
kubectl -n ai-routing rollout status deployment/gateway
```

For AWS EKS, use the equivalent `infrastructure/k8s/overlays/aws` overlay. Keep image tags, secrets, domains, and cloud credentials outside committed source.
