"""Deterministic HTTP mock for external provider contract tests.

This server is intentionally dependency-free and never contacts an external
provider. Select behavior with MOCK_PROVIDER_MODE=success|error|timeout.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class MockProviderHandler(BaseHTTPRequestHandler):
    server_version = "solvable-provider-mock/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Keep test output secret-free and deterministic.
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _mode(self) -> str:
        return os.getenv("MOCK_PROVIDER_MODE", "success").lower()

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/v1/models"}:
            self._json(200, {"status": "healthy", "service": "provider-mock"})
            return
        self._json(404, {"error": {"code": "not_found", "message": "Not found"}})

    def do_POST(self) -> None:  # noqa: N802
        mode = self._mode()
        if mode == "timeout":
            time.sleep(float(os.getenv("MOCK_PROVIDER_TIMEOUT_SECONDS", "2")))
            self._json(504, {"error": {"code": "upstream_timeout", "message": "Mock timeout"}})
            return
        if mode == "error":
            self._json(503, {"error": {"code": "provider_error", "message": "Mock provider unavailable"}})
            return

        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length) or b"{}")
        model = request.get("model", "mock-model")
        if self.path.endswith("/embeddings"):
            inputs = request.get("input", [])
            if isinstance(inputs, str):
                inputs = [inputs]
            self._json(
                200,
                {
                    "object": "list",
                    "data": [
                        {"object": "embedding", "index": index, "embedding": [0.1, 0.2, 0.3]}
                        for index, _ in enumerate(inputs)
                    ],
                    "model": model,
                    "provider": "mock",
                    "usage": {"prompt_tokens": len(inputs), "total_tokens": len(inputs)},
                },
            )
            return

        if request.get("stream"):
            events = [
                {"id": "mock-chat-0001", "object": "chat.completion.chunk", "created": 1_756_000_000, "model": model, "provider": "mock", "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]},
                {"id": "mock-chat-0001", "object": "chat.completion.chunk", "created": 1_756_000_000, "model": model, "provider": "mock", "choices": [{"index": 0, "delta": {"content": "READY"}, "finish_reason": None}]},
                {"id": "mock-chat-0001", "object": "chat.completion.chunk", "created": 1_756_000_000, "model": model, "provider": "mock", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
            ]
            body = "".join(f"data: {json.dumps(event, sort_keys=True)}\n\n" for event in events) + "data: [DONE]\n\n"
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        self._json(
            200,
            {
                "id": "mock-chat-0001",
                "object": "chat.completion",
                "created": 1_756_000_000,
                "model": model,
                "provider": "mock",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "READY"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 1, "total_tokens": 9, "estimated_cost_usd": 0.0},
                "generation_id": "gen_mock_0001",
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("MOCK_PROVIDER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MOCK_PROVIDER_PORT", "18003")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MockProviderHandler)
    print(f"provider-mock listening on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
