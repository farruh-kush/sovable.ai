from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
SERVICES = [
    ("auth", "services.auth.app", 8101),
    ("router", "services.router.app", 8102),
    ("provider", "services.provider.app", 8103),
    ("billing", "services.billing.app", 8104),
    ("gateway", "services.gateway.app", 8100),
]


def wait_for(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"timed out waiting for {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the standalone AI routing reference locally")
    parser.add_argument("--provider-mode", choices=["fake", "ollama"], default=os.getenv("PROVIDER_MODE", "fake"))
    args = parser.parse_args()
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "PROVIDER_MODE": args.provider_mode,
        "INTERNAL_SECRET": env.get("INTERNAL_SECRET", "local-dev-internal-secret"),
        "GATEWAY_API_KEY": env.get("GATEWAY_API_KEY", "sk-local-demo"),
        "AUTH_URL": "http://127.0.0.1:8101",
        "ROUTER_URL": "http://127.0.0.1:8102",
        "PROVIDER_URL": "http://127.0.0.1:8103",
        "BILLING_URL": "http://127.0.0.1:8104",
    })
    processes: list[subprocess.Popen[bytes]] = []

    def shutdown(*_: object) -> None:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        for name, module, port in SERVICES:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", f"{module}:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT,
                env=env,
            )
            processes.append(process)
            wait_for(f"http://127.0.0.1:{port}/health")
            print(f"{name} ready on :{port}", flush=True)
        print(f"All services are ready in provider mode={args.provider_mode}. Press Ctrl+C to stop.", flush=True)
        while True:
            failed = [(SERVICES[index][0], process.returncode) for index, process in enumerate(processes) if process.poll() is not None]
            if failed:
                raise RuntimeError(f"service exited unexpectedly: {failed}")
            time.sleep(1)
    finally:
        shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
