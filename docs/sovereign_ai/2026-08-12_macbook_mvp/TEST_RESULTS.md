# MacBook MVP Test Results

**Execution environment:** sandbox Linux host, Python 3.12, fake provider mode

## Automated tests

Command:

```bash
PROVIDER_MODE=fake USE_PRESIDIO=false PYTHONPATH=. pytest -q
```

Result:

```text
5 passed, 1 warning in 0.86s
```

The warning is Starlette’s deprecation warning about the installed `httpx` compatibility path for `TestClient`; it does not fail the suite.

## Static checks

```text
python3 -m compileall -q app.py privacy.py provider.py tests
```

Result: passed.

## HTTP smoke test

The local Uvicorn server was started on `127.0.0.1:8011` with `PROVIDER_MODE=fake`. The following endpoints returned successful responses:

| Endpoint | Result |
| --- | --- |
| `GET /health` | HTTP 200; `provider_mode=fake`. |
| `POST /v1/privacy/inspect` | HTTP 200; detected and masked email and PINFL-like value. |
| `POST /v1/chat/completions` | HTTP 200; fake provider received masked content and the response restored the email. |

## Ollama error-path test

The server was started on `127.0.0.1:8012` with `PROVIDER_MODE=ollama` while no Ollama runtime was running. The chat endpoint returned HTTP 502 with:

```text
Ollama request failed at http://localhost:11434/v1. Is Ollama running and is the model pulled?
```

This confirms that the gateway fails clearly instead of silently routing to an unknown provider.

## Defect found and fixed during testing

The first run exposed an email-recognizer boundary bug: a trailing sentence period prevented detection. The regex was corrected, and the full suite was rerun successfully with five passing tests.

## Not executed in the sandbox

The real Ollama inference path was not executed because the Ollama desktop runtime and model weights are not installed in the sandbox. The adapter follows Ollama’s documented local OpenAI-compatible endpoint. The README contains the MacBook commands for installing Ollama, pulling `llama3.2`, and running the real-provider smoke test.
