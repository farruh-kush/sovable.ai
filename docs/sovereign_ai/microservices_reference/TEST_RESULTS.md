# Verification Results

**Author:** Farruh

## Automated checks

| Check | Result |
| --- | --- |
| Python compilation: `python3 -m compileall -q shared services scripts tests` | Passed. |
| Unit/contract suite: `PYTHONPATH=. pytest -q` | **5 passed**, one non-failing Starlette/httpx deprecation warning. |
| Multi-process E2E: `PYTHONPATH=. python3 testing/scripts/e2e_smoke.py` | **Passed on ports 8200–8204.** |
| Compose structure parser: `python3 testing/scripts/validate_deployment.py` | **Compose structure valid.** |
| Docker image build and container runtime | Not executed because Docker is not installed in the sandbox. |

## E2E coverage

The E2E test boots the five services as separate Uvicorn processes, waits for each health endpoint, checks aggregate gateway readiness, verifies rejection without a bearer key, exercises local routing, confirms that an email is masked before provider processing and restored in the final response, verifies external routing rejection without explicit approval, verifies approved external routing, and confirms billing idempotency for duplicate request IDs.

## Provider behavior

The default provider is a deterministic fake adapter so the test suite does not require external credentials or model weights. The provider service contains an Ollama adapter path controlled by `PROVIDER_MODE=ollama` and `OLLAMA_BASE_URL`. The reference does not claim to have executed a real Ollama inference or a real external-provider call in the sandbox.

## Operational limitation

The reference uses in-memory auth keys, billing totals, and request-local privacy mappings. This is sufficient for contract and integration validation but not for production. The migration requirements are documented in `docs/ARCHITECTURE.md`.
