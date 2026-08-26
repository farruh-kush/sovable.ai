"""Bounded performance smoke test with deterministic thresholds.

Default is a read-only health endpoint. Chat/embedding workloads are allowed
only when PLATFORM_TARGET_ENV=staging and LOAD_ENABLE_MUTATIONS=1.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

PRODUCTION_HOSTS = {"api.sovable.ai", "sovable.ai", "www.sovable.ai"}


async def one(client: httpx.AsyncClient, method: str, url: str, body: dict | None, headers: dict[str, str]) -> tuple[float, int, str]:
    started = time.perf_counter()
    try:
        response = await client.request(method, url, json=body, headers=headers)
        return time.perf_counter() - started, response.status_code, ""
    except httpx.HTTPError as exc:
        return time.perf_counter() - started, 0, type(exc).__name__


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return float("inf")
    values = sorted(values)
    index = min(len(values) - 1, max(0, int(round((len(values) - 1) * fraction))))
    return values[index] * 1000


async def run(args: argparse.Namespace) -> int:
    parsed = urlparse(args.url)
    if parsed.hostname in PRODUCTION_HOSTS:
        print(json.dumps({"passed": False, "reason": "production_host_refused"}, sort_keys=True))
        return 1
    if args.method != "GET" and os.getenv("PLATFORM_TARGET_ENV") != "staging":
        print(json.dumps({"passed": False, "reason": "mutating_load_requires_staging"}, sort_keys=True))
        return 1
    if args.method != "GET" and os.getenv("LOAD_ENABLE_MUTATIONS") != "1":
        print(json.dumps({"passed": False, "reason": "set LOAD_ENABLE_MUTATIONS=1 for mutating workload"}, sort_keys=True))
        return 1

    body = None
    if args.body_file:
        body = json.loads(Path(args.body_file).read_text(encoding="utf-8"))
    headers = {}
    if os.getenv("PLATFORM_TEST_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['PLATFORM_TEST_API_KEY']}"
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        results = await asyncio.gather(*[one(client, args.method, args.url, body, headers) for _ in range(args.requests)])
    durations = [duration for duration, _, _ in results]
    failures = [item for item in results if item[1] < 200 or item[1] >= 500]
    p95 = percentile(durations, 0.95)
    error_rate = len(failures) / len(results) if results else 1.0
    passed = p95 <= args.p95_ms and error_rate <= args.max_error_rate
    report = {
        "passed": passed,
        "requests": len(results),
        "p50_ms": round(statistics.median(durations) * 1000, 2) if durations else None,
        "p95_ms": round(p95, 2),
        "max_ms": round(max(durations) * 1000, 2) if durations else None,
        "error_rate": round(error_rate, 4),
        "thresholds": {"p95_ms": args.p95_ms, "max_error_rate": args.max_error_rate},
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("LOAD_URL", "http://127.0.0.1:8000/health"))
    parser.add_argument("--method", choices=("GET", "POST"), default=os.getenv("LOAD_METHOD", "GET"))
    parser.add_argument("--body-file")
    parser.add_argument("--requests", type=int, default=int(os.getenv("LOAD_REQUESTS", "20")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("LOAD_TIMEOUT_SECONDS", "10")))
    parser.add_argument("--p95-ms", type=float, default=float(os.getenv("LOAD_P95_MS", "1000")))
    parser.add_argument("--max-error-rate", type=float, default=float(os.getenv("LOAD_MAX_ERROR_RATE", "0.01")))
    args = parser.parse_args()
    if args.requests < 1 or args.requests > 1000:
        parser.error("--requests must be between 1 and 1000")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
