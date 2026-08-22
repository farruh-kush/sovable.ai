#!/usr/bin/env python3
"""Fail when high-confidence live credential patterns are committed.

Author: Farruh

The scanner intentionally checks tracked files only and skips generated/vendor
roots. Explicit local, fake, demo, and replacement values are allowed;
real-looking provider, cloud, private-key, and token material is not.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_PARTS = {".git", "node_modules", "site", "out", ".next", "__pycache__"}
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Alibaba/AWS access key", re.compile(r"\b(?:LTAI|AKIA)[A-Z0-9]{12,}\b")),
    ("OpenAI-style secret", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "generic secret assignment",
        re.compile(
            r"(?i)(?<![A-Za-z0-9])(?:[A-Za-z0-9]+[_-])*"
            r"(?:api[_-]?key|access[_-]?key|secret(?:[_-]?key)?|password|token)"
            r"\s*[:=]\s*[\"'](?!\$|change-me|change_me|replace|example|placeholder|"
            r"fake|local|demo|test|e2e|integration|redacted|rand|admin|postgres|undefined|none|true|false|"
            r"sk-xyz|sk-replace)[^\"']{16,}[\"']"
        ),
    ),
)


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = []
    for raw in output.decode().split("\0"):
        if not raw:
            continue
        path = Path(raw)
        if SKIP_PARTS.intersection(path.parts):
            continue
        paths.append(ROOT / path)
    return paths


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: {label}")
    if findings:
        print("Potential committed secrets detected:")
        print("\n".join(findings))
        return 1
    print("Secret scan passed: no high-confidence live credential patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
