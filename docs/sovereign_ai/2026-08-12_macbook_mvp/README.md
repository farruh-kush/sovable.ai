# Build a Local Sovereign AI Gateway on a MacBook

**Author:** Farruh

This tutorial builds a small, local, OpenAI-compatible privacy gateway. It detects common sensitive values before they reach a model, replaces them with per-request tokens, sends only the masked request to a provider, and restores the values in the response. It supports a deterministic fake provider for tests and an optional local Ollama provider for real inference.

> **Important limitation.** This is a learning MVP, not a production security boundary. Its token mapping is held in process memory, it has no user authentication, it has no persistent audit store, and it uses regex recognizers unless optional Presidio mode is enabled. Do not use it with real bank-secret, government-restricted, health, or customer data.

## 1. What you will build

The request path is:

```text
Client
  → FastAPI gateway
  → detect PII and secrets
  → replace values with <TYPE_N> tokens
  → local fake provider or Ollama
  → restore values only in the response
  → OpenAI-compatible JSON response
```

The starter contains five small pieces:

| File | Purpose |
| --- | --- |
| `app.py` | FastAPI application with `/health`, `/v1/privacy/inspect`, and `/v1/chat/completions`. |
| `privacy.py` | Regex recognizers, optional Presidio integration, token mapping, masking, and restoration. |
| `provider.py` | Deterministic fake provider for tests or Ollama’s local OpenAI-compatible endpoint. |
| `tests/test_app.py` | Test coverage for detection, masking, restoration, multimodal text parts, health, and deferred streaming. |
| `requirements.txt` | Runtime and test dependencies. |

Ollama’s official documentation shows that its local OpenAI-compatible endpoint uses `http://localhost:11434/v1/`, accepts the placeholder API key `ollama`, and supports `/v1/chat/completions`. It also instructs users to pull a model before calling it [1]. Presidio’s Analyzer and Anonymizer documentation describes predefined/custom recognizers and operators such as replace, redact, mask, hash, and encrypt [2] [3].

## 2. Prerequisites

You need macOS, Python 3.11 or newer, a terminal, and `curl`. Confirm Python first:

```bash
python3 --version
curl --version
```

For real local model inference, install [Ollama for macOS](https://ollama.com/download/mac). The tutorial does not require Ollama for the first test run because the fake provider is deterministic and does not download a model.

## 3. Create the environment

From this tutorial directory:

```bash
cd /path/to/macbook_mvp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The current starter deliberately does not install Presidio or a spaCy model in the default path. The custom regex recognizers work with `USE_PRESIDIO=false`. To add richer recognizers later, install the optional dependencies with `python -m pip install -r requirements-presidio.txt`, then configure a compatible NLP model before setting `USE_PRESIDIO=true`.

## 4. Run the tests first

Run the deterministic test suite:

```bash
PROVIDER_MODE=fake USE_PRESIDIO=false PYTHONPATH=. pytest -q
```

The expected result is five passing tests. The tests verify that an email, PINFL-like identifier, phone number, and multimodal text parts are masked before the provider call and restored in the final response. FastAPI’s official testing guidance uses `TestClient` with pytest in this style [4].

## 5. Start the fake-provider gateway

Start the local API:

```bash
PROVIDER_MODE=fake USE_PRESIDIO=false PYTHONPATH=. \
  uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Keep that terminal open. In a second terminal, test health:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","provider_mode":"fake"}
```

Inspect a message without invoking a model:

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/privacy/inspect \
  -H 'content-type: application/json' \
  -d '{"text":"Contact alice@example.com; PINFL 12345678901234."}'
```

You should see `<EMAIL_1>` and `<PINFL_1>` in `masked_text`. The inspection response includes entity type, span, confidence, and whether Presidio is enabled. It does not return the original values.

Now send an OpenAI-compatible chat request:

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model":"local",
    "messages":[
      {"role":"user","content":"Send a receipt to alice@example.com."}
    ]
  }'
```

The fake provider receives a tokenized prompt internally, while the response returned to the client contains the original email. The response also includes an `x_privacy` object showing the number and types of detected entities.

## 6. Switch to a real local Ollama model

Stop the fake-provider server with `Control+C`. Start Ollama and pull a small model:

```bash
ollama pull llama3.2
```

Then restart the gateway in Ollama mode:

```bash
PROVIDER_MODE=ollama \
OLLAMA_BASE_URL=http://localhost:11434/v1 \
OLLAMA_MODEL=llama3.2 \
USE_PRESIDIO=false \
PYTHONPATH=. uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Call the same endpoint:

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model":"llama3.2",
    "messages":[
      {"role":"user","content":"Draft a polite reminder for alice@example.com about an overdue document."}
    ]
  }'
```

The gateway sends the model a prompt containing `<EMAIL_1>`, not the original email, and restores the email only in the response. You can confirm this behavior by temporarily adding structured logging inside `Provider._ollama_response`; do not log raw prompts in a real deployment.

If Ollama is unavailable, the endpoint returns HTTP 502 with a provider error. This is intentional: the gateway does not silently route to an unknown external service.

## 7. Understand the masking code

`PrivacyEngine.mask_text()` detects entities, sorts them by location and confidence, creates tokens such as `<EMAIL_1>`, and returns a mapping held only for the current request. `mask_messages()` applies the same logic to ordinary text messages and OpenAI-style multimodal text parts. `restore_payload()` walks the provider response recursively and restores values in strings, lists, and dictionaries.

The current recognizers are deliberately transparent and easy to extend:

| Entity | Example | MVP detector |
| --- | --- | --- |
| Email | `alice@example.com` | Regex |
| PINFL-like identifier | `12345678901234` | Fourteen-digit regex |
| Card-like value | `8600 1234 5678 9012` | Sixteen-digit regex with optional spaces/hyphens |
| Uzbek passport-like value | `AA1234567` | Prefix plus seven digits |
| Uzbekistan phone-like value | `+998 90 123 45 67` | Local format regex |
| TIN/STIR/INN | `TIN: 123456789` | Label plus nine digits |
| Secret assignment | `api_key=...` or `password:...` | Label plus non-space value |

These recognizers are not a complete Uzbek PII taxonomy. Add context, checksums, Cyrillic/Latin variants, health identifiers, addresses, names, account formats, legal classifications, source-code secrets, images, and document OCR before a serious pilot.

## 8. Optional Presidio mode

Install the optional dependencies first:

```bash
python -m pip install -r requirements-presidio.txt
export USE_PRESIDIO=true
```

Presidio may require an NLP model depending on the installed configuration. If initialization fails, the application intentionally stops with a clear error instead of pretending that richer detection is active. Begin with the regex-only mode, then add a tested Presidio configuration and language-specific recognizers.

Do not treat Presidio or any other detector as proof of complete anonymization. The local routing policy should fail closed for restricted data when detection confidence is low. The production architecture should combine deterministic recognizers, multilingual NER, secret scanners, OCR, file inspection, policy thresholds, and adversarial tests.

## 9. What this MVP does not implement

The code intentionally omits authentication, tenant isolation, encrypted persistent vault storage, HSM/KMS integration, audit/WORM storage, Redis rate limits, PostgreSQL usage ledgers, routing among multiple providers, circuit breakers, streaming SSE, RAG ingestion and ACL filtering, agent tool authorization, sandboxed code execution, image redaction, and billing. These are the next features for the five-service project: `gateway`, `auth`, `router`, `provider`, and `billing`.

The in-memory mapping is especially important. It demonstrates the idea but is not safe for production because mappings disappear on restart and are available to the process. A production vault should be tenant-scoped, encrypted, short-lived, access-controlled, audited, and protected with HSM/KMS-backed keys. For high-impact government or banking data, the preferred policy is local-only inference rather than relying on masking alone.

## 10. Suggested upgrade path into AI-Routing-Layer

First, move `PrivacyEngine` into the shared privacy domain package and keep the Gateway as the mandatory ingress boundary. Second, add a `router` service that receives only the canonical request and policy context, not raw unmasked content. Third, add `provider` adapters for Ollama, OpenAI-compatible APIs, Anthropic, Google, and Mistral with normalized errors and usage. Fourth, add `auth` and `billing` with separate PostgreSQL databases, while Redis remains ephemeral for rate limits, cooldowns, latency state, and cache entries. Fifth, add local RAG ingestion with document provenance, chunk ACL metadata, local embeddings, and retrieval authorization before context assembly. Sixth, add the agent capability broker, sandbox, human approval, and immutable audit path.

## 11. Test results from this tutorial build

The starter was executed in the sandbox before delivery. The deterministic suite completed with **5 passed tests**. An actual HTTP smoke test also passed for `/health`, `/v1/privacy/inspect`, and `/v1/chat/completions` using the fake provider. One recognizer defect was found during testing: a trailing sentence period prevented email detection because of an over-restrictive boundary. The regex was corrected and the full suite was rerun successfully.

The Ollama path is implemented against the official local OpenAI-compatible URL, but it was not executed in this sandbox because the Ollama desktop runtime and model weights are not available here. Run the Ollama section on your MacBook after installing the local runtime and pulling the model.

## References

[1]: <https://docs.ollama.com/api/openai-compatibility> “OpenAI compatibility,” Ollama documentation.

[2]: <https://microsoft.github.io/presidio/analyzer/> “Presidio Analyzer,” Microsoft Open Source documentation.

[3]: <https://microsoft.github.io/presidio/anonymizer/> “Presidio Anonymizer,” Microsoft Open Source documentation.

[4]: <https://fastapi.tiangolo.com/tutorial/testing/> “Testing,” FastAPI documentation.

[5]: <https://fastapi.tiangolo.com/advanced/testing-events/> “Testing Events: lifespan and startup-shutdown,” FastAPI documentation.
