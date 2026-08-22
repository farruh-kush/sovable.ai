# Deployment Guide

## Overview

This guide covers deploying the AI Routing Layer to staging and production environments using Kubernetes, Terraform, and GitHub Actions.

## Deployment Architecture

See `/docs/images/deployment-architecture.svg` for the complete infrastructure topology.

### Environments

| Environment | Cluster | DB | Cache | Scale |
|-------------|---------|----|----|-------|
| **Development** | Docker Compose | SQLite | In-Memory | 1 instance |
| **Staging** | K8s (single node) | PostgreSQL | Redis | 2 replicas |
| **Production** | K8s (3+ zones) | RDS Multi-AZ | Redis Cluster | 5-10 replicas |

## Prerequisites

- `kubectl` 1.24+
- `terraform` 1.0+
- `helm` 3.0+
- AWS CLI configured
- Docker CLI
- Git with SSH keys

## Local Development (Docker Compose)

### Start Services

```bash
# Build and start all services
docker compose up --build

# View logs
docker compose logs -f api

# Stop services
docker compose down

# Clean up (including data)
docker compose down -v
```

### Services Running

- API: http://127.0.0.1:8000
- Dashboard: http://127.0.0.1:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Prometheus: http://127.0.0.1:9090

## Staging Deployment

### Prerequisites Setup

```bash
# 1. Create AWS resources (VPC, RDS, ElastiCache)
cd infrastructure/observability/terraform/environments/staging
terraform init
terraform apply -var-file="staging.tfvars"

# 2. Create Kubernetes cluster (or use existing EKS)
aws eks create-cluster \
  --name routing-layer-staging \
  --version 1.27 \
  --region us-east-1 \
  ...

# 3. Configure kubectl
aws eks update-kubeconfig \
  --name routing-layer-staging \
  --region us-east-1
```

### Deploy to Staging

```bash
# 1. Build and push Docker image
docker build -t routing-layer:staging -f docker/Dockerfile .
docker tag routing-layer:staging 123456789.dkr.ecr.us-east-1.amazonaws.com/routing-layer:staging
aws ecr get-login-password | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/routing-layer:staging

# 2. Update Kubernetes manifests
sed -i 's|IMAGE_TAG|staging|g' infrastructure/observability/kubernetes/overlays/staging/kustomization.yaml

# 3. Apply Kubernetes manifests
kubectl apply -k infrastructure/observability/kubernetes/overlays/staging/

# 4. Verify deployment
kubectl get pods -l app=routing-layer
kubectl get svc routing-layer-api
kubectl logs -l app=routing-layer -f

# 5. Run smoke tests
./scripts/test-staging.sh
```

### Health Checks

```bash
# API health
curl https://staging-api.example.com/health

# Database connectivity
kubectl exec -it <pod-name> -- psql $DATABASE_URL -c "SELECT 1"

# Cache connectivity
kubectl exec -it <pod-name> -- redis-cli -u $REDIS_URL ping

# Provider connectivity
curl -X POST https://staging-api.example.com/v1/health \
  -H "Authorization: Bearer staging-key"
```

## Production Deployment

### Prerequisites Setup

```bash
# 1. Create production AWS resources
cd infrastructure/observability/terraform/environments/production
terraform init
terraform apply -var-file="production.tfvars"

# 2. Create multi-zone Kubernetes cluster
terraform apply -target=aws_eks_cluster.production -var-file="production.tfvars"

# 3. Configure kubectl
aws eks update-kubeconfig \
  --name routing-layer-prod \
  --region us-east-1
```

### Blue-Green Deployment

```bash
# 1. Deploy new version as "green"
kubectl set image deployment/routing-layer-blue \
  api=123456789.dkr.ecr.us-east-1.amazonaws.com/routing-layer:v1.2.0

# 2. Wait for health checks
kubectl rollout status deployment/routing-layer-blue

# 3. Switch traffic to green (update service selector)
kubectl patch service routing-layer-api \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# 4. Monitor for 5 minutes
# If issues detected, revert:
kubectl patch service routing-layer-api \
  -p '{"spec":{"selector":{"version":"green"}}}'

# 5. Once stable, update "green" with old version
kubectl set image deployment/routing-layer-green \
  api=<old-version-image>
```

### Canary Deployment (Alternative)

```bash
# 1. Deploy canary version (5% traffic)
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: routing-layer-api-canary
spec:
  selector:
    app: routing-layer
    version: v1.2.0-canary
  ports:
  - port: 8000
    targetPort: 8000
EOF

# 2. Monitor canary metrics
kubectl get pods -l version=v1.2.0-canary -w

# 3. Gradually increase traffic (using Istio/Flagger)
kubectl apply -f infrastructure/observability/kubernetes/istio/canary-rollout.yaml

# 4. Once stable, promote to production
kubectl scale deployment routing-layer-v1.2.0-canary --replicas=0
```

### Post-Deployment Verification

```bash
# 1. Health checks
curl -I https://api.example.com/health

# 2. Smoke tests
bash ./scripts/test-production.sh

# 3. Monitor dashboards
# - Grafana: https://monitoring.example.com
# - Prometheus: https://prometheus.example.com

# 4. Check logs
kubectl logs -l app=routing-layer -f --all-containers=true

# 5. Database integrity
kubectl exec -it <pod> -- python -m scripts.verify_db_integrity

# 6. Run synthetic tests
bash ./scripts/synthetic-tests.sh
```

## Rollback Procedures

### Immediate Rollback (< 1 minute)

```bash
# If using service selectors (fastest)
kubectl patch service routing-layer-api \
  -p '{"spec":{"selector":{"version":"previous"}}}'

# If using deployment, revert to previous
kubectl rollout undo deployment/routing-layer-api
```

### Full Rollback (< 5 minutes)

```bash
# 1. Stop new deployment
kubectl scale deployment routing-layer-api-v1.2.0 --replicas=0

# 2. Scale up old deployment
kubectl scale deployment routing-layer-api-v1.1.0 --replicas=5

# 3. Verify traffic is routed correctly
kubectl get pods -l app=routing-layer

# 4. Monitor metrics
# Should see traffic shift back to v1.1.0
```

### Database Rollback

```bash
# If database schema changes cause issues
# 1. Stop application
kubectl scale deployment routing-layer-api --replicas=0

# 2. Restore from previous snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier routing-layer-prod-restored \
  --db-snapshot-identifier routing-layer-prod-2024-06-01-00-00

# 3. Update connection string
kubectl set env deployment/routing-layer-api \
  DATABASE_URL=postgresql://...new-host...

# 4. Verify data integrity
kubectl run -it db-check --image=postgres:15 -- \
  psql postgresql://...new-host... -c "SELECT COUNT(*) FROM users"

# 5. Resume application
kubectl scale deployment routing-layer-api --replicas=5
```

## Monitoring & Observability

### Prometheus Setup

```bash
# Deploy Prometheus
kubectl apply -f infrastructure/observability/kubernetes/monitoring/prometheus.yaml

# Create PrometheusRule for alerts
kubectl apply -f infrastructure/observability/kubernetes/monitoring/prometheus-rules.yaml

# Port-forward to access
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

### Grafana Dashboards

```bash
# Deploy Grafana
kubectl apply -f infrastructure/observability/kubernetes/monitoring/grafana.yaml

# Access: http://localhost:3000 (after port-forward)
# Default credentials: admin/prom-operator
```

### View Logs (ELK Stack)

```bash
# Deploy ELK
kubectl apply -f infrastructure/observability/kubernetes/logging/elk.yaml

# Verify
kubectl get pods -n logging

# Kibana access
kubectl port-forward -n logging svc/kibana 5601:5601
# Open: http://localhost:5601
```

## Scaling

### Horizontal Scaling

```bash
# Check current replicas
kubectl get deployment routing-layer-api

# Scale up
kubectl scale deployment routing-layer-api --replicas=10

# Auto-scaling (requires HPA)
kubectl apply -f infrastructure/observability/kubernetes/hpa/routing-layer-hpa.yaml

# Verify
kubectl get hpa routing-layer-api -w
```

### Vertical Scaling

```bash
# Update resource requests/limits
kubectl set resources deployment routing-layer-api \
  --requests=cpu=1000m,memory=1Gi \
  --limits=cpu=2000m,memory=2Gi

# Check
kubectl get pods -o json | jq '.items[0].spec.containers[0].resources'
```

## Backup & Disaster Recovery

### Database Backups

```bash
# Enable automated backups
aws rds modify-db-instance \
  --db-instance-identifier routing-layer-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00"

# Manual backup
aws rds create-db-snapshot \
  --db-instance-identifier routing-layer-prod \
  --db-snapshot-identifier routing-layer-prod-manual-2024-06-02
```

### Restore from Backup

```bash
# List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier routing-layer-prod

# Restore to new instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier routing-layer-prod-restored \
  --db-snapshot-identifier routing-layer-prod-manual-2024-06-02
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name>

# View logs
kubectl logs <pod-name> --previous  # If crashed
kubectl logs <pod-name> -f           # Current logs

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

### High latency

```bash
# Check resource usage
kubectl top pods -l app=routing-layer
kubectl top nodes

# Check provider health
curl -H "Authorization: Bearer <key>" \
  http://api:8000/admin/providers/health

# Check database connections
kubectl exec -it <pod> -- psql $DATABASE_URL -c \
  "SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename;"
```

### Database issues

```bash
# Connection pool exhaustion
# Check: Max connections = 100 (RDS default)
# Solution: Scale to more pods or increase pool size

# Slow queries
kubectl exec -it <pod> -- psql $DATABASE_URL -c \
  "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

## Security Hardening

### Network Policies

```bash
# Restrict ingress to API
kubectl apply -f infrastructure/observability/kubernetes/network-policies/api-ingress.yaml

# Restrict egress (whitelist external APIs)
kubectl apply -f infrastructure/observability/kubernetes/network-policies/egress-providers.yaml
```

### RBAC

```bash
# Create service account
kubectl create serviceaccount routing-layer-app

# Create role
kubectl apply -f infrastructure/observability/kubernetes/rbac/routing-layer-role.yaml

# Bind role
kubectl create rolebinding routing-layer-app-binding \
  --clusterrole=routing-layer-role \
  --serviceaccount=default:routing-layer-app
```

## CI/CD Pipeline

See `.github/workflows/` for automated deployment pipelines.

### GitHub Actions Workflow

1. **Push to main** → Run tests → Build image → Push to ECR
2. **Create release** → Deploy to staging → Run integration tests
3. **Approval** → Deploy to production → Run smoke tests
4. **Failure** → Automatic rollback to previous version

