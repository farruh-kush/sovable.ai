# AI Agent Guidelines for the AI Routing Layer

This file contains instructions for AI agents working on the AI Routing Layer project.

**Author:** Farruh

## Architecture Principles

1. **Microservice Isolation:** The system is divided into 5 independent microservices (`gateway`, `auth`, `router`, `provider`, `billing`). Do not introduce tight coupling between them. They communicate exclusively via HTTP REST.
2. **Shared Library:** Domain models, exceptions, and common middleware reside in `shared/src/ai_routing_shared`. If a model is used by more than one service, it belongs in the shared library.
3. **Database Segregation:** `auth` and `billing` have their own isolated PostgreSQL databases (`auth_db` and `billing_db`). Do not attempt to join tables across these databases.
4. **State Management:** Redis is used for ephemeral state (rate limiting, prompt caching, latency tracking, monthly spend cache). Do not use Redis as a persistent system of record.

## Code Style

1. **Type Hinting:** Use strict Python 3.11+ type hints (`from __future__ import annotations`).
2. **Async Everything:** All I/O operations (HTTP requests, database queries, Redis calls) must be fully asynchronous using `httpx`, `asyncpg`, and `redis.asyncio`.
3. **Logging:** Use `structlog` for structured JSON logging. Always include contextual metadata (e.g., `generation_id`, `api_key_id`, `provider`).
4. **Error Handling:** Raise domain-specific exceptions from `ai_routing_shared.exceptions`. The Gateway's global error handler will map these to standard JSON responses.

## Development Workflow

1. **Schema Changes:** If you modify SQLAlchemy models in `auth` or `billing`, you MUST generate an Alembic migration using `alembic revision --autogenerate`.
2. **Configuration:** Do not hardcode routing rules, model limits, or pricing. Read them from `config/routing.yaml`.
3. **Adding Providers:** To add a new LLM provider:
   - Create a new adapter in `services/provider/src/provider/adapters/`.
   - Inherit from `BaseProviderAdapter`.
   - Register it in `ProviderRegistry`.
   - Add it to `config/routing.yaml`.

## Testing

When writing tests, use `pytest-asyncio`. Mock external HTTP calls using `respx` or by patching the `httpx.AsyncClient`.
