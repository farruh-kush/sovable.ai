"""Read-only HTTP health smoke utility.

Input format: --urls name=http://host/health,name2=http://host/health
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PRODUCTION_HOSTS = {"api.sovable.ai", "sovable.ai", "www.sovable.ai"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    checks = []
    passed = True
    for item in args.urls.split(","):
        if "=" not in item:
            passed = False
            checks.append({"name": item, "status": "failed", "reason": "expected name=url"})
            continue
        name, url = item.split("=", 1)
        parsed = urlparse(url)
        started = time.monotonic()
        if parsed.hostname in PRODUCTION_HOSTS:
            passed = False
            checks.append({"name": name, "status": "failed", "reason": "production_host_refused"})
            continue
        try:
            with urlopen(Request(url, method="GET"), timeout=args.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                ok = response.status == 200 and body.get("status") == "healthy"
                passed = passed and ok
                checks.append({"name": name, "status": "passed" if ok else "failed", "http_status": response.status, "service": body.get("service", "")})
        except Exception as exc:  # noqa: BLE001
            passed = False
            checks.append({"name": name, "status": "failed", "reason": type(exc).__name__})
        checks[-1]["duration_seconds"] = round(time.monotonic() - started, 3)
    print(json.dumps({"passed": passed, "checks": checks}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
