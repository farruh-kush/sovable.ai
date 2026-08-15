# Local tutorial research notes

## Verified setup references

Ollama’s official OpenAI-compatibility documentation shows a local base URL of `http://localhost:11434/v1/`, an API key value of `ollama` that is required by the client but ignored by Ollama, and `/v1/chat/completions` as a compatible endpoint. It documents chat completions, streaming, JSON mode, vision, tools, reasoning controls, `/v1/models`, and `/v1/embeddings`. The current docs tell users to pull a model before use, with `ollama pull llama3.2` as an example. Source: https://docs.ollama.com/api/openai-compatibility

Microsoft Presidio’s official Analyzer documentation says `AnalyzerEngine` runs predefined and custom recognizers using regex, NER, and other logic, and that `PatternRecognizer` can be extended for organization-specific entities. Presidio’s official Anonymizer documentation says `AnonymizerEngine` applies operators such as replace, redact, mask, hash, and encrypt, while `DeanonymizeEngine` can reverse encryption when the key is supplied. Presidio does not maintain stateful sessions, so this tutorial implements its own per-request token mapping rather than using a persistent global mapping. Sources: https://microsoft.github.io/presidio/analyzer/ and https://microsoft.github.io/presidio/anonymizer/

FastAPI’s official testing documentation uses `fastapi.testclient.TestClient` with pytest, and the lifespan documentation recommends using `with TestClient(app)` when startup/shutdown resources need to run. Source: https://fastapi.tiangolo.com/tutorial/testing/ and https://fastapi.tiangolo.com/advanced/testing-events/

## Tutorial scope

The MVP is deliberately local and testable without a running model: FastAPI endpoint, OpenAI-compatible request shape, custom regex recognizers for email/phone/PINFL/passport/bank-card-like values, reversible in-memory per-request tokens, response restoration, local-provider adapter to Ollama, health endpoint, and tests using a fake provider. It is a learning build, not a production security boundary. The code must explicitly warn that the in-memory vault is process-local and that production requires encrypted, tenant-scoped storage with HSM/KMS-backed keys, authentication, audit, rate limits, and fail-closed routing.
