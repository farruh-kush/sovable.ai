---
title: API quickstart
sidebar_label: Quickstart
---

# API quickstart

The Solvable API is OpenAI-compatible at the baseline. The public gateway is `https://api.sovable.ai`.

## Create an API key

Sign in to the User Portal, open **API keys**, and create a key with the smallest required scope. Store the value in a secret manager or environment variable. Do not commit it, put it in browser source, or send it to a third party.

```bash
export SOVABLE_API_KEY='replace-with-your-key'
```

## Chat completion

```bash
curl https://api.sovable.ai/v1/chat/completions \
  -H "Authorization: Bearer $SOVABLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-plus",
    "messages": [
      {"role": "user", "content": "Explain governed AI routing in one paragraph."}
    ],
    "temperature": 0.2
  }'
```

The response uses a normalized chat-completion shape. Provider-specific details are represented in normalized metadata where available, while the client contract remains stable.

## Streaming

Set `stream` to `true` to receive Server-Sent Events. Each data event contains a normalized delta. The stream ends with `[DONE]`.

```bash
curl -N https://api.sovable.ai/v1/chat/completions \
  -H "Authorization: Bearer $SOVABLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"Stream a short greeting."}],"stream":true}'
```

## Embeddings

```bash
curl https://api.sovable.ai/v1/embeddings \
  -H "Authorization: Bearer $SOVABLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-v4","input":"Solvable control plane"}'
```

## Errors and observability

Errors use a consistent JSON envelope with an error type, message, request identifier, and optional retry information. Record the request identifier when opening support or investigating an incident. Do not log authorization headers or raw prompt content.

The generated [API Reference](reference.md) is rebuilt from the gateway OpenAPI document during the documentation build. It is the source for exact paths, request schemas, responses, and authentication requirements.
