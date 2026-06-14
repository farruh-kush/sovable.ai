# Infrastructure as Code

## Folders

- `kubernetes/` - Kubernetes manifests (K8s deployments)
- `terraform/` - Terraform configurations (AWS provisioning)
- `scripts/` - Infrastructure scripts

## Deployment

See main `/docs/DEPLOYMENT.md` for complete procedures.

### Kubernetes
```bash
kubectl apply -k kubernetes/overlays/staging/
```

### Terraform
```bash
cd terraform/environments/staging
terraform init
terraform apply -var-file="staging.tfvars"
```
