# Test Plan & Remaining Work

**Date:** June 17, 2026  
**Author:** Farruh Kushnazarov  
**Project:** AI Routing Layer (Microservice Architecture)

---

## 1. Overview

The AI Routing Layer has successfully migrated to a robust microservice architecture (`gateway`, `router`, `provider`, `auth`, `billing`). The production blockers (Alembic migrations, CORS, and test suite alignment) have been resolved.

This document outlines the comprehensive testing strategy for the new microservices and identifies the remaining development tasks before the platform can be considered fully feature-complete according to the original product specification.

---

## 2. Comprehensive Test Plan

The current test files (`services/*/tests/test_*.py`) are placeholders (`assert True`). They must be populated according to the following strategy.

### 2.1. Shared Library (`ai-routing-shared`)
**Focus:** Pure unit tests with no external dependencies.
*   **Models:** Verify Pydantic validation rules, default values, and schema serialization for `ChatCompletionRequest`, `ProviderPreferences`, and `UsageRecord`.
*   **Utils:** Test `hash_api_key` with known inputs/outputs.
*   **Middleware:** Verify `RequestIdMiddleware` injects UUIDs and `error_handler_middleware` correctly maps domain exceptions to HTTP status codes.

### 2.2. Auth Service
**Focus:** Database integration and validation logic.
*   **API Key Creation:** Verify keys are generated, hashed, and persisted correctly. Ensure the raw key is only returned once.
*   **Validation:** Test `/internal/validate-key` with valid, invalid, and expired keys. Verify the `ApiKey` principal object is correctly hydrated with tier limits and model whitelists.
*   **Mocking:** Use `pytest-asyncio` and an in-memory SQLite database or a test PostgreSQL container.

### 2.3. Billing Service
**Focus:** Financial math and Redis integration.
*   **Cost Calculation:** Unit test `PricingCatalog` extensively. Verify math for prompt tokens, completion tokens, platform markup, and the 50% discount for `cached_tokens`.
*   **Usage Ingestion:** Verify the `/internal/usage` endpoint correctly persists `UsageRecordORM` to the database.
*   **Redis Spend Cache:** Mock the Redis client and verify `_update_monthly_spend` correctly increments the float value and sets the TTL to the end of the month.

### 2.4. Provider Adapter Service
**Focus:** Request normalization and HTTP client resilience.
*   **Adapter Mocks:** Use `respx` to mock external calls to `api.openai.com` and `api.anthropic.com`.
*   **Normalization:** Verify OpenAI and Anthropic specific responses are correctly mapped into the unified `ChatCompletionResponse` schema.
*   **Streaming:** Test the SSE chunk generator for both providers, ensuring deltas are correctly formatted.
*   **Error Handling:** Force HTTP 500s and 429s from the mocked providers and verify they raise `ProviderError` with the correct `retriable` flag.

### 2.5. Router Engine Service
**Focus:** Routing logic, fallback chains, and latency tracking.
*   **Static Routing:** Verify the engine selects the correct primary provider based on `routing.yaml`.
*   **Fallback Chains:** Mock a failing primary provider and verify the engine transparently retries the request against the fallback provider.
*   **Latency Optimization:** Mock the Redis client to return specific P50 latencies, and verify `_sort_by_latency` correctly orders the candidates.
*   **Data Policy:** Test `ProviderPreferences(data_collection="deny")` and verify providers without ZDR are stripped from the candidate list.

### 2.6. API Gateway Service
**Focus:** End-to-end integration and policy enforcement.
*   **Budget Enforcement:** Mock the Redis spend cache to return a value higher than the API key's budget, and verify the request is rejected with HTTP 429.
*   **Model Whitelist:** Test requesting a model not in the API key's `allowed_models` list and verify HTTP 403.
*   **Prompt Caching:** Mock the Redis cache. Send an identical request twice; verify the second request does not hit the router and returns `X-Cache: HIT`.

---

## 3. Remaining Work (Post-Launch Backlog)

The following items are not deployment blockers, but are required to achieve full feature parity with the original product specification.

| Task | Component | Description | Priority |
| :--- | :--- | :--- | :--- |
| **Google Gemini Adapter** | Provider | Implement `GoogleAdapter` in `services/provider/src/provider/adapters/google_adapter.py` using the Gemini API. | High |
| **Mistral Adapter** | Provider | Implement `MistralAdapter` in `services/provider/src/provider/adapters/mistral_adapter.py`. | High |
| **Implement Tests** | All Services | Replace the `assert True` placeholders with the tests outlined in Section 2. | High |
| **Observability Stack** | Infrastructure | Deploy Prometheus and Grafana (or Alibaba Cloud ARMS) to scrape the `/metrics` endpoints of all microservices. | Medium |
| **A/B Testing Engine** | Router | Implement Phase 4 (Task 4.3) to randomly split traffic between models/providers based on an `experiment_name` header. | Low |
| **Admin Web Dashboard** | Web | Complete the Next.js dashboard in `web/dashboard/` to allow UI-based API key generation and usage visualization. | Low |
