# Local Development Deployment Guide

This guide provides step-by-step instructions for deploying the AI Routing Layer on your local machine for development and testing purposes.

**Author:** Farruh

## Overview

**Use-case:** A developer needs to run the entire AI Routing Layer locally to test API integrations, modify routing logic, or develop new features.
**Pain point:** Running 5 microservices, 2 databases, Redis, and an observability stack manually is complex, error-prone, and leads to "it works on my machine" issues.
**Solution:** A unified Docker Compose stack that builds all services from source, provisions databases, and runs migrations automatically in a single command.

---

## Prerequisites

Before starting, ensure you have the following installed on your local machine:

1. **Docker Desktop** (or Docker Engine + Docker Compose plugin)
   - Must be running and allocated at least 4GB of RAM.
2. **Git**
3. **curl** (for testing the API)

## Step 1: Clone the Repository

Clone the repository and navigate to the project root:

```bash
git clone https://github.com/k-farruh/ai-routing-platform.git
cd ai-routing-platform
```

## Step 2: Configure Environment Variables

The project requires several environment variables to run. A template is provided in `.env.example`.

1. Copy the template to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in your preferred text editor.
3. (Optional) Add your LLM provider API keys. If you leave these blank, the Provider service will still start, but requests to those providers will fail unless you configure mock responses.
   ```env
   OPENAI_API_KEY=sk-proj-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

## Step 3: Start the Platform

We use Docker Compose to build the microservices and start the infrastructure.

1. Run the following command from the project root:
   ```bash
   docker compose up --build -d
   ```
   *The `-d` flag runs the containers in the background (detached mode).*

2. Wait approximately 30-60 seconds for all services to start. The `auth` and `billing` services will automatically run Alembic database migrations during their startup sequence.

3. Verify all services are healthy:
   ```bash
   docker compose ps
   ```
   You should see `gateway`, `auth`, `router`, `provider`, `billing`, `postgres`, `redis`, `prometheus`, `grafana`, `loki`, and `promtail` all marked as `Up (healthy)`.

## Step 4: Create an API Key

The Gateway service requires a valid API key to accept requests. You must create one using the Admin API.

Run the following `curl` command:

```bash
curl -X POST http://localhost:8000/v1/keys \
  -H "X-Admin-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Local Dev Key",
    "tier": "pro",
    "monthly_budget_usd": 100.0
  }'
```

*Note: `change-me-in-production` is the default `ADMIN_API_KEY` in `.env.example`.*

The response will look like this:
```json
{
  "id": "key_abc123",
  "name": "Local Dev Key",
  "key": "sk-abc123def456ghi789",
  "tier": "pro"
}
```
**Save the `key` value (`sk-...`). You will need it for the next step.**

## Step 5: Test the Gateway

Now you can send an OpenAI-compatible chat completion request to your local Gateway.

Replace `<YOUR_API_KEY>` with the key you generated in Step 4:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "What is the capital of France?"}]
  }'
```

If successful, you will receive a standard OpenAI-format response, routed through the local platform.

## Step 6: Access Observability Tools

The local stack includes a full observability suite.

* **Grafana (Metrics & Dashboards):** `http://localhost:3000`
  * Username: `admin`
  * Password: `admin` (or the value of `GRAFANA_PASSWORD` in `.env`)
* **Prometheus (Raw Metrics):** `http://localhost:9090`
* **Gateway Swagger UI (API Docs):** `http://localhost:8000/docs`

## Troubleshooting

**Logs:** To view the logs of a specific service (e.g., the router):
```bash
docker compose logs -f router
```

**Database Reset:** If you need to completely wipe the local databases and start fresh:
```bash
docker compose down -v
docker compose up --build -d
```
*(Warning: This will delete your local API keys and usage history).*
