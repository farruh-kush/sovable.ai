---
title: API reference
sidebar_label: Generated API reference
---

# AI Routing Layer — API Gateway

This page is generated from the gateway OpenAPI contract during every documentation build. The source specification is available as [openapi.json](./openapi.json).

**OpenAPI version:** `3.1.0`
**API version:** `0.1.0`

## `POST /auth/logout`

Logout

**Tags:** `Authentication`

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |

## `GET /auth/me`

Me

**Tags:** `Authentication`

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |

## `GET /auth/oauth/{provider}/callback`

Oauth Callback

**Tags:** `Authentication`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `provider` | `path` | yes | `string` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `GET /auth/oauth/{provider}/start`

Oauth Start

**Tags:** `Authentication`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `provider` | `path` | yes | `string` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `POST /auth/refresh`

Refresh

**Tags:** `Authentication`

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |

## `POST /auth/register/{channel}/start`

Register Start

**Tags:** `Authentication`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `channel` | `path` | yes | `string` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `POST /auth/register/{channel}/verify`

Register Verify

**Tags:** `Authentication`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `channel` | `path` | yes | `string` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `GET /health`

Health

**Tags:** `Health`

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |

## `GET /v1/admin/overview`

Admin Overview

**Tags:** `Admin`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `X-Admin-Key` | `header` | no | `object` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `POST /v1/chat/completions`

Chat Completions

**Tags:** `Chat Completions`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `authorization` | `header` | no | `object` |  |
| `x-api-key` | `header` | no | `object` |  |

### Request body

```json
{
  "required": true,
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/ChatCompletionRequest"
      }
    }
  }
}
```

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `POST /v1/embeddings`

Embeddings

**Tags:** `Embeddings`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `authorization` | `header` | no | `object` |  |
| `x-api-key` | `header` | no | `object` |  |

### Request body

```json
{
  "required": true,
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/EmbeddingRequest"
      }
    }
  }
}
```

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `GET /v1/generations/{generation_id}`

Get Generation

**Tags:** `Generations`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `generation_id` | `path` | yes | `string` |  |
| `authorization` | `header` | no | `object` |  |
| `x-api-key` | `header` | no | `object` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `GET /v1/keys`

List Keys

**Tags:** `API Keys`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `x-admin-key` | `header` | no | `object` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `POST /v1/keys`

Create Key

**Tags:** `API Keys`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `x-admin-key` | `header` | no | `object` |  |

### Request body

```json
{
  "required": true,
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/CreateKeyRequest"
      }
    }
  }
}
```

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

## `GET /v1/models`

List Models

**Tags:** `Models`

### Parameters

| Name | In | Required | Type | Description |
|---|---|---:|---|---|
| `authorization` | `header` | no | `object` |  |
| `x-api-key` | `header` | no | `object` |  |

### Responses

| Status | Description |
|---:|---|
| `200` | Successful Response |
| `422` | Validation Error |

