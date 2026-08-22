# Kubernetes deployment for the standalone AI Routing reference

**Author:** Farruh

This package deploys the synchronized five-service reference implementation: gateway, auth, router, provider, and billing. It is intentionally separate from the repository’s existing `infrastructure/k8s/` manifests so it can be evaluated and rolled out independently.

## Build and publish the image

Build the single reference image from `docs/sovereign_ai/microservices_reference`:

```bash
docker build -t ghcr.io/YOUR_ORG/ai-routing-reference:0.1.0 docs/sovereign_ai/microservices_reference
docker push ghcr.io/YOUR_ORG/ai-routing-reference:0.1.0
```

Replace `ghcr.io/replace-me/ai-routing-reference:0.1.0` in `deployments.yaml` or apply a Kustomize image override:

```bash
kubectl -n ai-routing-reference kustomize . >/tmp/ai-routing-reference.yaml
sed -i.bak 's#ghcr.io/replace-me/ai-routing-reference:0.1.0#ghcr.io/YOUR_ORG/ai-routing-reference:0.1.0#g' /tmp/ai-routing-reference.yaml
```

## Create runtime secrets

Do not apply `secret.template.yaml` with placeholder values. Use an external secret manager in production. For a development cluster:

```bash
kubectl create namespace ai-routing-reference
kubectl -n ai-routing-reference create secret generic runtime-secrets \
  --from-literal=internal-secret="$(openssl rand -hex 32)" \
  --from-literal=gateway-api-key="sk-local-demo" \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Deploy

```bash
kubectl apply -k .
kubectl -n ai-routing-reference rollout status deployment/gateway
kubectl -n ai-routing-reference get pods,svc,ingress
```

The ingress assumes an NGINX ingress controller and a TLS Secret named `gateway-tls`. Change the hostname and TLS integration for the target government or banking cluster.

## Security boundary

The namespace enables the restricted Pod Security Standard labels. Pods run as non-root, use a RuntimeDefault seccomp profile, drop Linux capabilities, use a read-only root filesystem, and receive only an in-memory `/tmp`. The internal services are ClusterIP-only. The ingress exposes only the gateway. Network policies deny ingress by default, permit same-namespace service traffic and ingress-controller traffic, and permit DNS plus same-namespace egress.

The reference still uses in-memory auth, billing, and privacy state. For a production cluster, replace those implementations with PostgreSQL/Redis and an encrypted KMS/HSM-backed privacy vault; use External Secrets or a cloud-native secret manager rather than Kubernetes Secret literals.

## Validation

```bash
kubectl kustomize . >/tmp/ai-routing-reference.yaml
kubectl apply --dry-run=client -k .
```
