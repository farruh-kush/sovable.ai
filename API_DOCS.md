# AI Routing Layer — API Documentation

This document outlines the public-facing API endpoints exposed by the API Gateway Service.

**Author:** Farruh

## Base URL

In local development: `http://localhost:8000`

## Authentication

All endpoints (except `/health`) require an API key passed via the `Authorization` header:

```http
Authorization: Bearer sk-your-api-key-here
```

---

## 1. Chat Completions

**Endpoint:** `POST /v1/chat/completions`

OpenAI-compatible chat completions endpoint. Routes the request to the optimal provider based on the configured strategy.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | The model alias to route (e.g., `gpt-4o`, `claude-3-5-sonnet-20241022`, `cheapest`, `fastest`). |
| `messages` | array | Yes | Array of message objects (`role`, `content`). |
| `temperature` | float | No | Sampling temperature (0.0 to 2.0). Default: `0.7`. |
| `max_tokens` | integer | No | Maximum number of tokens to generate. |
| `stream` | boolean | No | Whether to stream the response via Server-Sent Events (SSE). Default: `false`. |
| `provider` | object | No | Advanced routing preferences. |

#### Advanced Routing Preferences (`provider` object)

| Field | Type | Description |
|-------|------|-------------|
| `order` | array | Explicit fallback chain override (e.g., `["anthropic", "openai"]`). |
| `sort` | string | Dynamic sorting strategy: `latency` or `price`. |
| `data_collection` | string | Set to `deny` to only route to Zero Data Retention (ZDR) providers. |
| `allow_fallbacks` | boolean | Whether to allow fallback to other providers on failure. Default: `true`. |

### Response Headers

The response will include the following custom headers:

* `X-Generation-Id`: Unique ID for the generation (use this to fetch activity logs).
* `X-Cache`: `HIT` or `MISS` (indicates if the response was served from the gateway prompt cache).

---

## 2. Embeddings

**Endpoint:** `POST /v1/embeddings`

OpenAI-compatible embeddings endpoint.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | The embedding model (e.g., `text-embedding-3-small`). |
| `input` | string/array | Yes | The text string or array of strings to embed. |

---

## 3. Models

**Endpoint:** `GET /v1/models`

Lists all available models, their primary providers, and data policy tags.

### Response Example

```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4o",
      "object": "model",
      "provider": "openai",
      "data_policy": {
        "trains_on_data": false,
        "zero_data_retention": true,
        "gdpr_compliant": true,
        "data_residency": ["us", "eu"]
      }
    }
  ]
}
```

---

## 4. Activity Logs (Generations)

**Endpoint:** `GET /v1/generations/{generation_id}`

Retrieve detailed metadata, token usage, and cost breakdown for a specific generation. You can only retrieve generations created by your API key.

### Response Example

```json
{
  "id": "gen_abc123",
  "model": "gpt-4o",
  "provider": "openai",
  "created_at": "2026-06-14T10:00:00Z",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 50,
    "total_tokens": 200,
    "cached_tokens": 0,
    "cache_discount_usd": 0.0,
    "cache_hit": false
  },
  "cost": {
    "prompt_cost_usd": 0.00075,
    "completion_cost_usd": 0.00075,
    "cache_discount_usd": 0.0,
    "total_cost_usd": 0.0015,
    "markup_usd": 0.0000825,
    "billed_usd": 0.0015825
  },
  "latency_ms": 1250.5,
  "fallback_used": false,
  "cache_hit": false
}
```

---

## 5. API Keys (Admin Only)

**Endpoint:** `POST /v1/keys`

Create a new API key. Requires the `X-Admin-Key` header instead of `Authorization`.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable name for the key. |
| `tier` | string | No | The routing tier (`free`, `pro`, `enterprise`). Default: `free`. |
| `monthly_budget_usd` | float | No | Hard monthly budget cap in USD. |
| `allowed_models` | array | No | Whitelist of allowed models. |
