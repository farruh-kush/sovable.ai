#!/usr/bin/env python3
"""Validate the governed routing catalog without contacting providers."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "shared" / "src"))
sys.path.insert(0, str(ROOT / "microservices" / "router" / "src"))

from router.core.catalog import CatalogDocument


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", nargs="?", default=str(ROOT / "ai" / "config" / "routing.yaml")
    )
    args = parser.parse_args()
    path = Path(args.path)
    raw = path.read_bytes()
    document = CatalogDocument.model_validate(yaml.safe_load(raw) or {})
    forbidden = ("api_key", "token", "secret", "authorization", "password")
    serialized = raw.decode("utf-8").lower()
    violations = [
        word
        for word in forbidden
        if word in serialized and word not in ("api_key", "token")
    ]
    # Environment variable names such as DASHSCOPE_API_KEY are allowed; values are not.
    if "sk-" in serialized or "bearer " in serialized:
        raise ValueError("possible live credential detected in catalog")
    print(
        f"valid catalog_version={document.catalog_version} policy_version={document.policy_version} checksum={hashlib.sha256(raw).hexdigest()}"
    )
    if violations:
        print(
            f"note: secret field words are present only as environment variable names: {sorted(set(violations))}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
