"""Verify rollback readiness without mutating a cluster by default.

The default mode performs manifest render and records the required rollback
commands. Applying rollback requires --apply-staging and an explicit staging
namespace; production namespaces are rejected.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_NAMESPACES = {"ai-routing", "production", "prod", "default"}


def command(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=120)
    return result.returncode, (result.stdout + "\n" + result.stderr)[-4000:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default=os.getenv("ROLLBACK_NAMESPACE", "ai-routing-staging"))
    parser.add_argument("--deployment", default="gateway")
    parser.add_argument("--apply-staging", action="store_true")
    args = parser.parse_args()
    if args.namespace in PRODUCTION_NAMESPACES:
        print(json.dumps({"passed": False, "reason": "production_namespace_refused"}, sort_keys=True))
        return 1
    started = time.monotonic()
    checks = []
    code, output = command(["kubectl", "kustomize", "infrastructure/k8s/overlays/alibaba"])
    checks.append({"name": "render-current-manifest", "passed": code == 0, "output_tail": output})
    if code != 0:
        print(json.dumps({"passed": False, "checks": checks}, sort_keys=True))
        return 1
    rollback = ["kubectl", "rollout", "undo", f"deployment/{args.deployment}", "-n", args.namespace]
    if args.apply_staging:
        if os.getenv("PLATFORM_TARGET_ENV") != "staging":
            print(json.dumps({"passed": False, "reason": "rollback_apply_requires_staging"}, sort_keys=True))
            return 1
        code, output = command(rollback)
        checks.append({"name": "apply-staging-rollback", "passed": code == 0, "output_tail": output})
        if code == 0:
            code, output = command(["kubectl", "rollout", "status", f"deployment/{args.deployment}", "-n", args.namespace, "--timeout=120s"])
            checks.append({"name": "verify-staging-rollout", "passed": code == 0, "output_tail": output})
    else:
        checks.append({"name": "rollback-command-reviewed", "passed": True, "command": " ".join(rollback), "output_tail": "read-only verification; no rollback applied"})
    report = {"passed": all(check["passed"] for check in checks), "namespace": args.namespace, "deployment": args.deployment, "duration_seconds": round(time.monotonic() - started, 3), "checks": checks}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
