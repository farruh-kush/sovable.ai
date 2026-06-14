# ─────────────────────────────────────────────────────────────────────────────
# AI Routing Layer — Makefile
#
# Provides convenience commands for local development, cloud dev, and
# cloud production deployments.
#
# Usage:
#   make help
#
# Author: Farruh
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help \
        local-up local-down local-logs local-reset local-key local-test \
        dev-deploy dev-update dev-logs \
        prod-build prod-push prod-deploy prod-update prod-status \
        lint test

REGISTRY   ?= ghcr.io/k-farruh
VERSION    ?= $(shell git rev-parse --short HEAD)
NAMESPACE  ?= ai-routing
SERVICES   := gateway auth router provider billing

# ── Help ─────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "  AI Routing Layer — Makefile"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Local Development ─────────────────────────────────────────────────────────

local-up: ## Build and start the full local stack (all services + infra)
	docker compose up --build -d
	@echo ""
	@echo "  Platform is starting. Run 'make local-logs' to follow logs."
	@echo "  Gateway:   http://localhost:8000/docs"
	@echo "  Grafana:   http://localhost:3000"
	@echo "  Prometheus: http://localhost:9090"
	@echo ""

local-down: ## Stop and remove all local containers (keeps volumes)
	docker compose down

local-reset: ## Completely wipe local state (containers + volumes)
	docker compose down -v
	@echo "All containers and volumes removed."

local-logs: ## Follow logs from all services
	docker compose logs -f gateway auth router provider billing

local-key: ## Create a local dev API key (requires local stack to be running)
	@echo "Creating local dev API key..."
	@curl -s -X POST http://localhost:8000/v1/keys \
		-H "X-Admin-Key: change-me-in-production" \
		-H "Content-Type: application/json" \
		-d '{"name":"Local Dev Key","tier":"pro","monthly_budget_usd":100.0}' | python3 -m json.tool

local-test: ## Run a test chat completion against the local gateway
	@if [ -z "$(KEY)" ]; then \
		echo "Usage: make local-test KEY=sk-your-api-key"; exit 1; \
	fi
	@curl -s -X POST http://localhost:8000/v1/chat/completions \
		-H "Authorization: Bearer $(KEY)" \
		-H "Content-Type: application/json" \
		-d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello!"}]}' | python3 -m json.tool

# ── Cloud Dev (Staging) ───────────────────────────────────────────────────────

dev-deploy: ## Deploy to the cloud dev VM via SSH (Usage: make dev-deploy HOST=user@host)
	@if [ -z "$(HOST)" ]; then \
		echo "Usage: make dev-deploy HOST=user@your-server-ip"; exit 1; \
	fi
	ssh $(HOST) "cd /opt/ai-routing-platform && sudo git pull origin master && sudo docker compose up --build -d"
	@echo "Cloud dev deployment complete."

dev-logs: ## Stream logs from the cloud dev VM (Usage: make dev-logs HOST=user@host)
	@if [ -z "$(HOST)" ]; then \
		echo "Usage: make dev-logs HOST=user@your-server-ip"; exit 1; \
	fi
	ssh $(HOST) "cd /opt/ai-routing-platform && sudo docker compose logs -f gateway router"

# ── Cloud Production (Kubernetes) ────────────────────────────────────────────

prod-build: ## Build all Docker images tagged with the current git SHA
	@echo "Building images with tag: $(VERSION)"
	@for svc in $(SERVICES); do \
		echo "  Building $$svc..."; \
		docker build -t $(REGISTRY)/ai-routing-$$svc:$(VERSION) -f services/$$svc/Dockerfile . ; \
	done
	@echo "All images built."

prod-push: ## Push all Docker images to the container registry
	@echo "Pushing images with tag: $(VERSION) to $(REGISTRY)"
	@for svc in $(SERVICES); do \
		echo "  Pushing $$svc..."; \
		docker push $(REGISTRY)/ai-routing-$$svc:$(VERSION); \
	done
	@echo "All images pushed."

prod-deploy: ## Deploy all manifests to the Kubernetes cluster
	kubectl apply -f k8s/base/namespace.yaml
	kubectl apply -f k8s/base/secrets.yaml
	kubectl create configmap routing-config \
		--from-file=config/routing.yaml -n $(NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f k8s/base/hpa.yaml
	kubectl apply -f k8s/services/microservices.yaml
	kubectl apply -f k8s/services/gateway.yaml
	@echo "Production deployment applied."

prod-update: ## Update image tags in K8s deployments to current VERSION
	@echo "Rolling out version $(VERSION) to all services..."
	@for svc in $(SERVICES); do \
		kubectl set image deployment/$$svc $$svc=$(REGISTRY)/ai-routing-$$svc:$(VERSION) -n $(NAMESPACE); \
	done
	@echo "Rollout triggered. Run 'make prod-status' to monitor."

prod-status: ## Check the status of all pods and HPAs in the cluster
	@echo "=== Pods ==="
	kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "=== HPAs ==="
	kubectl get hpa -n $(NAMESPACE)
	@echo ""
	@echo "=== Ingress ==="
	kubectl get ingress -n $(NAMESPACE)

prod-routing-update: ## Update routing config in K8s without redeploying code
	kubectl create configmap routing-config \
		--from-file=config/routing.yaml -n $(NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl rollout restart deployment router -n $(NAMESPACE)
	@echo "Routing config updated and router restarted."

# ── Development Utilities ─────────────────────────────────────────────────────

lint: ## Run Python linting (ruff) across all services
	ruff check services/ shared/

test: ## Run the test suite
	pytest tests/ -v
