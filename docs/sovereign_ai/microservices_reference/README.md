# AI Routing Layer — Standalone Microservices Reference

**Author:** Farruh

This folder is a self-contained reference implementation of the AI Routing Layer. It demonstrates working REST integration between five services:

| Service | Port | Role |
| --- | ---: | --- |
| Gateway | 8100 | Public OpenAI-compatible API and orchestration. |
| Auth | 8101 | API-key and scope validation. |
| Router | 8102 | Model allowlist, residency policy, cost metadata, and fallback chain. |
| Provider | 8103 | Provider adapter boundary with deterministic fake mode and optional Ollama mode. |
| Billing | 8104 | Quota preflight, idempotent usage recording, monthly spend, and alerts. |

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=. python3 testing/scripts/e2e_smoke.py
```

The E2E runner starts all five services on ports `8200–8204`, uses the deterministic fake provider, and terminates all child processes after the checks complete. The expected result is:

```text
E2E smoke test passed on ports 8200-8204
```

To run the long-lived local stack on the default ports:

```bash
PYTHONPATH=. python3 testing/scripts/run_local.py --provider-mode fake
```

Then call the gateway:

```bash
curl -sS http://127.0.0.1:8100/ready
curl -sS -X POST http://127.0.0.1:8100/v1/chat/completions \
  -H 'Authorization: Bearer sk-local-demo' \
  -H 'content-type: application/json' \
  -d '{"model":"local","messages":[{"role":"user","content":"Send a receipt to alice@example.com."}]}'
```

The response includes an `x_routing` object with the selected provider, model, request ID, masked entity count, latency, and usage-recording status. The provider receives `<EMAIL_1>` rather than the original email, and the gateway restores the value only in the final response.

## Docker Compose

```bash
docker compose up --build
curl -sS http://127.0.0.1:8100/ready
```

The sandbox used for validation did not contain the Docker executable, so Compose was checked by YAML parsing and service-structure assertions rather than by building containers. The local multi-process runtime was executed successfully.

## Tests

```bash
python3 -m compileall -q shared services scripts tests
PYTHONPATH=. pytest -q
PYTHONPATH=. python3 testing/scripts/e2e_smoke.py
python3 testing/scripts/validate_deployment.py
```

The tested reference currently passes five unit/contract tests, a multi-process E2E test covering authentication, readiness, local routing, PII masking and restoration, external-policy rejection, approved external routing, and billing idempotency, plus Compose structure validation.

## Architecture and production boundary

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the service contracts, request sequence, privacy boundary, failure semantics, deployment topology, production migration map, and known gaps. The reference is deliberately self-contained and uses in-memory state; production deployment must replace that state with PostgreSQL, Redis, encrypted vault/KMS, mTLS/workload identity, durable usage outbox, persistent policy management, and provider-specific adapters.

The default fake provider is a test adapter, not a language model. Set `PROVIDER_MODE=ollama` and run the local stack only after an Ollama-compatible local model is available. External providers remain simulated in this reference and must be replaced with audited adapters and approved egress policies.
