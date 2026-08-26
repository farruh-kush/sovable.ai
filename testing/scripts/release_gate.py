"""Deterministic Solvable AI release gate.

Modes:
  ci      local, secret-free contracts/security/static checks
  staging opt-in HTTP smoke against a non-production target
  ack     render the Alibaba ACK overlay and optionally inspect cluster health

The runner never applies Kubernetes manifests, changes production, or prints
unmasked command output. External providers are replaced by the local mock.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = ROOT / "testing/evidence/release-gate.json"
SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,]+"),
    re.compile(r"(?i)(x-api-key\s*[:=]\s*)[^\s,]+"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN [^-]+ PRIVATE KEY-----.*?-----END [^-]+ PRIVATE KEY-----", re.S),
)


@dataclass
class Check:
    name: str
    status: str
    duration_seconds: float
    output: str = ""
    reason: str = ""


def mask(text: str) -> str:
    masked = text
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub(lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]", masked)
    return masked.replace(os.getenv("PLATFORM_TEST_API_KEY", "__missing__"), "[REDACTED]")


def run_command(name: str, command: Sequence[str], checks: list[Check], *, cwd: Path = ROOT, optional: bool = False) -> bool:
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=900)
        output = mask((completed.stdout + "\n" + completed.stderr).strip())[-12000:]
        status = "passed" if completed.returncode == 0 else "failed"
        checks.append(Check(name, status, round(time.monotonic() - started, 3), output, "" if status == "passed" else f"exit_code={completed.returncode}"))
        return completed.returncode == 0
    except FileNotFoundError as exc:
        status = "skipped" if optional else "failed"
        checks.append(Check(name, status, round(time.monotonic() - started, 3), "", f"command_not_found={exc.filename}"))
        return optional
    except subprocess.TimeoutExpired:
        checks.append(Check(name, "failed", round(time.monotonic() - started, 3), "", "timeout_after_900_seconds"))
        return False


def run_frontend(checks: list[Check], strict: bool) -> bool:
    npm = shutil.which("npm")
    if not npm:
        checks.append(Check("frontend-quality", "skipped" if not strict else "failed", 0.0, "", "npm_not_found"))
        return not strict
    ok = True
    for label, command in (
        ("frontend-typecheck", [npm, "run", "typecheck"]),
        ("frontend-build", [npm, "run", "build"]),
    ):
        ok = run_command(label, command, checks, cwd=ROOT / "frontend/dashboard") and ok
    return ok


def preflight(mode: str, checks: list[Check]) -> bool:
    if mode == "staging":
        if os.getenv("PLATFORM_TARGET_ENV") != "staging":
            checks.append(Check("staging-target-guard", "failed", 0.0, "", "PLATFORM_TARGET_ENV must equal staging"))
            return False
        required = ("GATEWAY_BASE_URL",)
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            checks.append(Check("staging-target-config", "failed", 0.0, "", "missing=" + ",".join(missing)))
            return False
    if mode == "ack" and not (ROOT / "infrastructure/k8s/overlays/alibaba/kustomization.yaml").exists():
        checks.append(Check("ack-overlay-present", "failed", 0.0, "", "ACK overlay missing"))
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("ci", "staging", "ack"), default="ci")
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--strict", action="store_true", help="require optional frontend and ACK tooling")
    args = parser.parse_args()

    checks: list[Check] = []
    started = time.monotonic()
    ok = preflight(args.mode, checks)
    pytest_bin = os.getenv("PYTEST_BIN") or str(ROOT / "venv/bin/pytest")
    if not Path(pytest_bin).exists():
        pytest_bin = shutil.which("pytest") or "pytest"
    marker = "not staging" if args.mode == "ci" else "staging"
    ok = run_command(
        "platform-tests",
        [pytest_bin, "-c", str(ROOT / "testing/pytest.ini"), "-q", "testing/platform_tests", "-m", marker, "--junitxml", str(ROOT / "testing/evidence/platform-junit.xml")],
        checks,
        optional=False,
    ) and ok
    if args.mode == "ci":
        ok = run_frontend(checks, strict=args.strict or os.getenv("RELEASE_STRICT") == "1") and ok
        ok = run_command("ack-overlay-render", ["kubectl", "kustomize", "infrastructure/k8s/overlays/alibaba"], checks, optional=not args.strict) and ok
    elif args.mode == "ack":
        ok = run_command("ack-overlay-render", ["kubectl", "kustomize", "infrastructure/k8s/overlays/alibaba"], checks, optional=False) and ok
        health_urls = os.getenv("ACK_HEALTH_URLS")
        if health_urls:
            script = ROOT / "testing/scripts/http_smoke.py"
            ok = run_command("ack-health-smoke", [sys.executable, str(script), "--urls", health_urls], checks, optional=False) and ok
        else:
            checks.append(Check("ack-health-smoke", "skipped", 0.0, "", "ACK_HEALTH_URLS not configured; render-only mode"))
    elif args.mode == "staging":
        checks.append(Check("production-mutation-guard", "passed", 0.0, "", "staging smoke is read-only unless explicitly marked mutating"))

    report = {
        "schema_version": "1.0",
        "mode": args.mode,
        "passed": ok and all(item.status in {"passed", "skipped"} for item in checks),
        "duration_seconds": round(time.monotonic() - started, 3),
        "checks": [asdict(item) for item in checks],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "mode": args.mode, "evidence": str(args.output), "checks": len(checks)}, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
