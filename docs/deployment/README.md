# Deployment Guides

This directory contains step-by-step deployment guides for the AI Routing Layer across all three target environments.

**Author:** Farruh

| Guide | Environment | Description |
|---|---|---|
| [LOCAL.md](./LOCAL.md) | Local Development | Docker Compose on your laptop. Single command startup, includes full observability stack. |
| [CLOUD_DEV.md](./CLOUD_DEV.md) | Cloud Dev / Staging | Docker Compose on a single cloud VM with Nginx + SSL. Shared team environment. |
| [CLOUD_PROD.md](./CLOUD_PROD.md) | Cloud Production | Kubernetes (EKS/GKE/AKS) with HPA, managed databases, and zero-downtime deployments. |

## Quick Reference

A root-level `Makefile` provides convenience commands for all three environments. Run `make help` from the project root to see all available commands.
