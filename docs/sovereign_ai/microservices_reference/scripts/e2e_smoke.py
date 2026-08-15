from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
INTERNAL_SECRET = "e2e-internal-secret"
API_KEY = "sk-e2e-demo"
BASE_PORT = int(os.getenv("E2E_BASE_PORT", "8200"))
PORTS = {
    "gateway": BASE_PORT,
    "auth": BASE_PORT + 1,
    "router": BASE_PORT + 2,
    "provider": BASE_PORT + 3,
    "billing": BASE_PORT + 4,
}
SERVICES = [
    ("auth", "services.auth.app"),
    ("router", "services.router.app"),
    ("provider", "services.provider.app"),
    ("billing", "services.billing.app"),
    ("gateway", "services.gateway.app"),
]


def url(name: str) -> str:
    return f"http://127.0.0.1:{PORTS[name]}"


def wait_for(client: httpx.Client, target: str) -> None:
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            response = client.get(f"{target}/health")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise AssertionError(f"service did not become healthy: {target}")


def usage_payload() -> dict[str, object]:
    return {
        "request_id": "idempotency-1",
        "principal": {
            "api_key_id": "key",
            "subject": "user",
            "organization_id": "org",
            "tier": "paid",
            "scopes": [],
        },
        "provider": "local-fake",
        "model": "local-fake",
        "input_tokens": 1,
        "output_tokens": 1,
        "latency_ms": 1,
        "estimated_cost_usd": 1.0,
    }


def main() -> int:
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "INTERNAL_SECRET": INTERNAL_SECRET,
        "GATEWAY_API_KEY": API_KEY,
        "PROVIDER_MODE": "fake",
        "AUTH_URL": url("auth"),
        "ROUTER_URL": url("router"),
        "PROVIDER_URL": url("provider"),
        "BILLING_URL": url("billing"),
        "MONTHLY_BUDGET_USD": "100",
    })
    processes: list[subprocess.Popen[bytes]] = []
    try:
        with httpx.Client(timeout=10) as client:
            for name, module in SERVICES:
                process = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", f"{module}:app", "--host", "127.0.0.1", "--port", str(PORTS[name])],
                    cwd=ROOT,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                processes.append(process)
                wait_for(client, url(name))
                print(f"PASS {name} health")

            gateway = url("gateway")
            ready = client.get(f"{gateway}/ready")
            assert ready.status_code == 200 and ready.json()["ready"] is True, ready.text
            print("PASS gateway readiness")

            unauthorized = client.post(
                f"{gateway}/v1/chat/completions",
                json={"model": "local", "messages": [{"role": "user", "content": "hello"}]},
            )
            assert unauthorized.status_code == 401, unauthorized.text
            print("PASS authentication rejection")

            local = client.post(
                f"{gateway}/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "X-Request-ID": "e2e-local-1"},
                json={
                    "model": "local",
                    "messages": [{"role": "user", "content": "Send a receipt to alice@example.com."}],
                },
            )
            assert local.status_code == 200, local.text
            local_body = local.json()
            assert "alice@example.com" in local_body["choices"][0]["message"]["content"]
            assert local_body["x_routing"]["masked_entity_count"] == 1
            assert local_body["x_routing"]["provider"] == "local-fake"
            print("PASS local routing + PII masking + response restoration + usage recording")

            external_denied = client.post(
                f"{gateway}/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )
            assert external_denied.status_code == 403, external_denied.text
            print("PASS external residency policy rejection")

            external_allowed = client.post(
                f"{gateway}/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "metadata": {"allow_external": True},
                    "messages": [{"role": "user", "content": "Summarize alice@example.com."}],
                },
            )
            assert external_allowed.status_code == 200, external_allowed.text
            assert external_allowed.json()["x_routing"]["provider"] == "external-fake"
            print("PASS approved external routing")

            first = client.post(
                f"{url('billing')}/internal/usage",
                headers={"X-Internal-Secret": INTERNAL_SECRET},
                json=usage_payload(),
            )
            second = client.post(
                f"{url('billing')}/internal/usage",
                headers={"X-Internal-Secret": INTERNAL_SECRET},
                json=usage_payload(),
            )
            assert first.status_code == 200 and second.status_code == 200
            assert first.json()["monthly_cost_usd"] == second.json()["monthly_cost_usd"]
            print("PASS billing idempotency")
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    print(f"E2E smoke test passed on ports {BASE_PORT}-{BASE_PORT + 4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
