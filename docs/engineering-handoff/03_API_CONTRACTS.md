# Solvable API Contracts

**Author:** Farruh  
**Version:** 1.0  
**Status:** Engineering kickoff baseline

## 1. Contract rules

All APIs are versioned. Public APIs use `/v1`; control-plane APIs use `/api/v1`; internal APIs use an explicit service contract version in the path or header. Breaking changes require a new version. Additive fields are allowed when clients must ignore unknown fields. Dates are RFC 3339 UTC. IDs are opaque strings, preferably UUIDv7 or another sortable UUID. Amounts are decimal strings or integer minor units; never use binary floating-point for money.

Every response includes:

```json
{
  "request_id": "req_01J...",
  "data": {},
  "error": null,
  "meta": {
    "api_version": "v1",
    "schema_version": "1"
  }
}
```

Streaming responses use `text/event-stream`, send normalized `id`, `event`, and `data` fields, and terminate with `data: [DONE]`. A stream may send a final usage event before `[DONE]` if usage is available.

## 2. Authentication and headers

| Header | Required | Purpose |
|---|---:|---|
| `Authorization: Bearer <api_key>` | Public API | Scoped API-key authentication. |
| `X-Request-ID` | Optional | Client-supplied idempotent correlation ID; server generates one if absent. |
| `Idempotency-Key` | Required for mutations with side effects | Prevent duplicate create, install, charge, or run operations. |
| `X-Organization-ID` | Optional | Only for authorized multi-organization administrators; server must verify membership. |
| `X-Project-ID` | Optional | Selects project scope; server must verify key and principal scope. |
| `If-Match` | Required for selected updates | Optimistic concurrency using resource version/ETag. |

The browser console uses a secure session mechanism and must not store long-lived API keys in local storage. API keys are shown only at creation and never returned by list endpoints.

## 3. Public AI API

### 3.1 `POST /v1/chat/completions`

The endpoint accepts an OpenAI-compatible baseline plus Solvable extensions. Provider-specific extensions must be namespaced under `solvable` or rejected according to policy.

Example request:

```json
{
  "model": "qwen-plus",
  "messages": [
    {"role": "system", "content": "You are concise."},
    {"role": "user", "content": "Explain provider-independent routing."}
  ],
  "temperature": 0.2,
  "stream": false,
  "solvable": {
    "route_policy": "balanced-default",
    "data_policy": "standard-masking",
    "cache": {"mode": "read-write"},
    "metadata": {"application": "docs"}
  }
}
```

Example normalized response:

```json
{
  "id": "chatcmpl_sol_01J...",
  "object": "chat.completion",
  "created": 1786800000,
  "model": "qwen-plus",
  "provider": "alibaba-model-studio",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "..."},
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 31,
    "completion_tokens": 42,
    "total_tokens": 73,
    "cached_tokens": 0
  },
  "solvable": {
    "request_id": "req_01J...",
    "route_id": "route_01J...",
    "route_policy": "balanced-default",
    "provider_attempts": 1,
    "cache_status": "miss",
    "data_policy": "masked",
    "estimated_provider_cost": "0.000123",
    "estimated_customer_charge": "0.000148"
  }
}
```

The exact provider and route metadata returned to end users is controlled by organization policy. A privacy-sensitive tenant may receive only a route class rather than provider name.

### 3.2 Streaming behavior

```text
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
X-Request-ID: req_01J...

id: chunk_1
event: completion.chunk
data: {"id":"...","choices":[{"delta":{"role":"assistant"}}]}

id: usage_1
event: completion.usage
data: {"prompt_tokens":31,"completion_tokens":42,"total_tokens":73}

data: [DONE]
```

If a provider fails after a stream has emitted content, the platform must not silently replay from another provider unless the request policy explicitly allows a continuation strategy. The stream sends a typed terminal error or ends with a safe incomplete status.

### 3.3 `POST /v1/embeddings`

Example request:

```json
{
  "model": "text-embedding-v4",
  "input": ["first text", "second text"],
  "encoding_format": "float"
}
```

The response includes `object`, `data`, `model`, `usage`, and Solvable metadata. The platform must validate vector dimensions against the model catalog and must not silently mix dimensions within one request.

### 3.4 `GET /v1/models`

The caller sees only models allowed by organization, project, API key, region, data policy, quota, and provider health.

```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen-plus",
      "object": "model",
      "owned_by": "alibaba-model-studio",
      "capabilities": {"chat": true, "streaming": true, "embeddings": false},
      "context_window": 131072,
      "availability": "available",
      "price_version": "price_2026_08_01"
    }
  ]
}
```

## 4. Public request status and usage

### `GET /v1/requests/{request_id}`

Returns caller-scoped metadata, status, route class, provider attempts where permitted, latency, token usage, cache state, data-policy result, and estimated cost. It does not return raw prompt or response unless retention and caller policy permit it.

### `GET /v1/usage`

Supports `from`, `to`, `project_id`, `model`, `provider`, `status`, `group_by`, and pagination. Usage values are labeled as measured, estimated, reconciled, or pending.

## 5. Control-plane API

### 5.1 Identity and organization

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create a pending account. |
| `POST` | `/api/v1/auth/login` | Establish a secure session. |
| `POST` | `/api/v1/auth/logout` | Revoke current session. |
| `POST` | `/api/v1/auth/verify` | Verify email or enrollment challenge. |
| `POST` | `/api/v1/auth/password/reset` | Start or complete reset. |
| `GET` | `/api/v1/me` | Current principal and effective permissions. |
| `GET/POST` | `/api/v1/organizations` | List or create organizations according to role. |
| `GET/PATCH` | `/api/v1/organizations/{id}` | Read or update organization settings. |
| `GET/POST` | `/api/v1/organizations/{id}/members` | List or invite members. |
| `PATCH` | `/api/v1/organizations/{id}/members/{member_id}` | Change role or status. |
| `GET/POST` | `/api/v1/projects` | List or create projects within an organization. |

### 5.2 API keys

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/keys` | List metadata only. |
| `POST` | `/api/v1/projects/{project_id}/keys` | Create and show a key exactly once. |
| `POST` | `/api/v1/keys/{key_id}/rotate` | Revoke old key and create replacement. |
| `POST` | `/api/v1/keys/{key_id}/revoke` | Revoke immediately. |
| `PATCH` | `/api/v1/keys/{key_id}` | Update name, scopes, expiry, allowlists, or status where permitted. |

Create response:

```json
{
  "key": {
    "id": "key_01J...",
    "name": "production-api",
    "prefix": "sol_abc123",
    "secret": "shown-once",
    "scopes": ["chat:write", "embeddings:write"],
    "expires_at": "2027-08-16T00:00:00Z"
  },
  "warning": "Store this secret now. It cannot be retrieved later."
}
```

### 5.3 Providers, models, and routes

| Method | Path | Purpose |
|---|---|---|
| `GET/POST` | `/api/v1/providers` | List or register provider configurations. |
| `GET/PATCH` | `/api/v1/providers/{id}` | Read or update a provider. |
| `POST` | `/api/v1/providers/{id}/test` | Run a bounded health/capability test. |
| `GET/POST` | `/api/v1/models` | List or register model metadata. |
| `PATCH` | `/api/v1/models/{id}` | Approve, disable, alias, or update model metadata. |
| `GET/POST` | `/api/v1/routing/policies` | List or create policy versions. |
| `POST` | `/api/v1/routing/policies/{id}/simulate` | Simulate without upstream invocation. |
| `POST` | `/api/v1/routing/policies/{id}/activate` | Activate a version after authorization. |
| `POST` | `/api/v1/routing/policies/{id}/rollback` | Revert to the prior valid version. |

### 5.4 Privacy

| Method | Path | Purpose |
|---|---|---|
| `GET/POST` | `/api/v1/privacy/policies` | List or create masking/retention policies. |
| `POST` | `/api/v1/privacy/policies/{id}/test` | Evaluate test fixtures. |
| `POST` | `/api/v1/privacy/simulate` | Show transformed output without upstream call. |
| `PATCH` | `/api/v1/privacy/policies/{id}` | Update a draft policy. |
| `POST` | `/api/v1/privacy/policies/{id}/activate` | Activate a reviewed version. |

### 5.5 Marketplace

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/store/apps` | Search approved apps and agents. |
| `GET` | `/api/v1/store/apps/{app_id}` | Read manifest, permissions, version, and security status. |
| `POST` | `/api/v1/store/apps/{app_id}/install` | Request installation with approval context. |
| `POST` | `/api/v1/store/installations/{id}/rollback` | Roll back installed version. |
| `POST` | `/api/v1/store/publishers` | Register publisher. |
| `POST` | `/api/v1/store/packages` | Submit signed package and manifest. |
| `POST` | `/api/v1/store/packages/{id}/approve` | Approve after review. |

## 6. Internal service contracts

Internal services use service authentication, mTLS or an authenticated network, explicit timeouts, retry classification, and an internal request ID. Service-to-service responses must not expose provider secrets or raw sensitive payloads.

### 6.1 Auth validation

`POST /internal/v1/auth/validate-key`

```json
{
  "api_key": "provided-in-memory-only",
  "request_id": "req_01J...",
  "required_scopes": ["chat:write"],
  "project_id": "proj_01J..."
}
```

Response:

```json
{
  "principal": {
    "subject_id": "user_01J...",
    "organization_id": "org_01J...",
    "project_id": "proj_01J...",
    "key_id": "key_01J...",
    "roles": ["developer"],
    "scopes": ["chat:write"],
    "limits": {"rpm": 60, "monthly_budget": "100.00"}
  },
  "decision": "allow",
  "policy_version": "iam_2026_08_01"
}
```

### 6.2 Router selection

`POST /internal/v1/routes/select`

The request includes normalized model request, capability requirements, principal policy context, data-policy result, budget state, candidate catalog, and request deadline. The response includes selected route, candidate explanations, fallback chain, policy version, and route-decision ID.

### 6.3 Provider invocation

`POST /internal/v1/providers/{provider_id}/invoke` and `POST /internal/v1/providers/{provider_id}/stream` accept a normalized request plus a provider model identifier and secret reference. The provider adapter returns normalized result, usage, provider request ID, latency, raw status class, and typed error if applicable.

## 7. Error contract

```json
{
  "error": {
    "type": "policy_violation",
    "code": "MODEL_NOT_ALLOWED",
    "message": "The requested model is not enabled for this project.",
    "param": "model",
    "retryable": false,
    "request_id": "req_01J...",
    "details": {"policy_version": "policy_01J..."}
  }
}
```

Required error classes include `authentication_error`, `authorization_error`, `validation_error`, `rate_limit_error`, `quota_exceeded`, `budget_exceeded`, `policy_violation`, `provider_unavailable`, `provider_timeout`, `provider_rate_limit`, `upstream_invalid_response`, `stream_interrupted`, `dependency_unavailable`, and `internal_error`.

Messages must be safe for end users. Internal diagnostics belong in structured logs and restricted traces.

## 8. Pagination and filtering

List endpoints use cursor pagination:

```json
{"data": [], "has_more": true, "next_cursor": "cur_01J..."}
```

Filters must be allowlisted and indexed. User-supplied sort fields must never be concatenated into SQL. Admin exports are asynchronous for large ranges and return an export job ID.

## 9. Compatibility and deprecation

Public response fields are additive by default. A field removal requires a deprecation notice, documentation, telemetry for remaining callers, and a migration window. Provider-specific parameters are namespaced. Internal contracts use contract tests and consumer-driven compatibility tests.
