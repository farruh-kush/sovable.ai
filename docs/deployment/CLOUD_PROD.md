# Cloud Production Deployment Guide (Kubernetes)

This guide details how to deploy the AI Routing Layer to a production-grade Kubernetes cluster. This architecture is designed for high availability, automatic scaling, and zero-downtime deployments.

**Author:** Farruh

## Overview

**Use-case:** An enterprise requires a highly available, scalable AI routing infrastructure to handle thousands of concurrent requests across multiple LLM providers.
**Pain point:** A single VM or monolithic deployment cannot handle sudden traffic spikes, nor does it provide fault tolerance if a process crashes or a node fails.
**Solution:** A Kubernetes-based microservice architecture utilizing Horizontal Pod Autoscalers (HPA), isolated node pools, and external managed databases (RDS/ElastiCache) to guarantee uptime and performance.

---

## Prerequisites

1. **A Kubernetes Cluster:** EKS (AWS), GKE (Google Cloud), or AKS (Google Cloud) running Kubernetes v1.28+.
2. **Managed PostgreSQL:** E.g., AWS RDS PostgreSQL 16+.
3. **Managed Redis:** E.g., AWS ElastiCache Redis 7+.
4. **CLI Tools:** `kubectl`, `helm`, and your cloud provider's CLI (e.g., `aws`, `gcloud`) configured locally.
5. **Container Registry:** E.g., AWS ECR, Docker Hub, or GitHub Packages to store your built Docker images.
6. **Ingress Controller:** An Nginx Ingress Controller or AWS ALB Ingress Controller installed on the cluster.

---

## Step 1: Build and Push Docker Images

Before deploying to Kubernetes, you must build the Docker images for all 5 microservices and push them to your container registry.

From the project root, run the build and push commands (replace `YOUR_REGISTRY` with your actual registry URL):

```bash
export REGISTRY="YOUR_REGISTRY"
export VERSION=$(git rev-parse --short HEAD)

# Build
docker build -t $REGISTRY/ai-routing-gateway:$VERSION -f microservices/gateway/Dockerfile .
docker build -t $REGISTRY/ai-routing-auth:$VERSION -f microservices/auth/Dockerfile .
docker build -t $REGISTRY/ai-routing-router:$VERSION -f microservices/router/Dockerfile .
docker build -t $REGISTRY/ai-routing-provider:$VERSION -f microservices/provider/Dockerfile .
docker build -t $REGISTRY/ai-routing-billing:$VERSION -f microservices/billing/Dockerfile .

# Push
docker push $REGISTRY/ai-routing-gateway:$VERSION
docker push $REGISTRY/ai-routing-auth:$VERSION
docker push $REGISTRY/ai-routing-router:$VERSION
docker push $REGISTRY/ai-routing-provider:$VERSION
docker push $REGISTRY/ai-routing-billing:$VERSION
```

---

## Step 2: Configure Secrets

Do not commit raw secrets to version control. We will use the provided template to create the secrets manually in the cluster.

1. Copy the template:
   ```bash
   cp infrastructure/k8s/base/secrets.yaml.template infrastructure/k8s/base/secrets.yaml
   ```

2. Edit `infrastructure/k8s/base/secrets.yaml` and replace all placeholder values (`REPLACE_WITH_...`) with your actual production credentials.
   *Ensure your PostgreSQL URLs point to your managed RDS instance, and Redis URLs point to your ElastiCache instance.*

3. Create the namespace and apply the secrets:
   ```bash
   kubectl apply -f infrastructure/k8s/base/namespace.yaml
   kubectl apply -f infrastructure/k8s/base/secrets.yaml
   ```

*(Best Practice: In a true enterprise environment, use ExternalSecrets, AWS Secrets Manager, or HashiCorp Vault instead of static Secret objects).*

---

## Step 3: Apply the Routing Configuration

The Router service requires the `routing.yaml` file to be mounted as a ConfigMap.

Create the ConfigMap from the local file:

```bash
kubectl create configmap routing-config \
  --from-file=ai/config/routing.yaml \
  -n ai-routing \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## Step 4: Update Image Tags in Manifests

You must update the Kubernetes manifests to use the specific image tags you pushed in Step 1.

Using `sed` (Linux) or manually editing the files, replace `latest` with your `$VERSION` tag in `infrastructure/k8s/services/gateway.yaml` and `infrastructure/k8s/services/microservices.yaml`. Also, ensure the image paths point to your `$REGISTRY`.

Example manual edit in `gateway.yaml`:
```yaml
      containers:
        - name: gateway
          image: YOUR_REGISTRY/ai-routing-gateway:a1b2c3d
```

---

## Step 5: Deploy the Microservices

Apply the Horizontal Pod Autoscalers (HPA) and the service manifests:

```bash
# Apply HPAs
kubectl apply -f infrastructure/k8s/base/hpa.yaml

# Apply Microservices (Auth, Router, Provider, Billing)
kubectl apply -f infrastructure/k8s/services/microservices.yaml

# Apply Gateway (Deployment, Service, and Ingress)
kubectl apply -f infrastructure/k8s/services/gateway.yaml
```

---

## Step 6: Verify the Deployment

1. **Check Pod Status:**
   ```bash
   kubectl get pods -n ai-routing
   ```
   All pods should transition to the `Running` state within a few minutes.

2. **Check HPA Status:**
   ```bash
   kubectl get hpa -n ai-routing
   ```
   You should see targets for CPU and Memory utilization.

3. **Check Ingress:**
   ```bash
   kubectl get ingress -n ai-routing
   ```
   Note the `ADDRESS` assigned to your Gateway Ingress. Update your DNS provider to point your domain (e.g., `api.yourdomain.com`) to this address.

---

## Step 7: Database Migrations (Important Note)

In this architecture, the `auth` and `billing` containers are configured to run `alembic upgrade head` as their entrypoint. In a Kubernetes environment with multiple replicas starting simultaneously, this can cause race conditions.

**Production Recommendation:**
Remove the migration command from the Dockerfile entrypoint, and instead execute migrations using a Kubernetes `Job` or an init-container before deploying the main replica sets.

---

## Updating Routing Rules (Zero Downtime)

To update routing rules, pricing, or add new models without redeploying code:

1. Update your local `ai/config/routing.yaml`.
2. Update the ConfigMap:
   ```bash
   kubectl create configmap routing-config --from-file=ai/config/routing.yaml -n ai-routing --dry-run=client -o yaml | kubectl apply -f -
   ```
3. Perform a rollout restart of the Router deployment to pick up the new ConfigMap:
   ```bash
   kubectl rollout restart deployment router -n ai-routing
   ```
