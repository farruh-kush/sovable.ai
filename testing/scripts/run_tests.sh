#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTEST="${PYTEST_BIN:-$PYTHON_BIN -m pytest}"

export PYTHONPATH="$ROOT/backend/shared/src:$ROOT/microservices/auth/src:$ROOT/microservices/billing/src:$ROOT/microservices/gateway/src:$ROOT/microservices/provider/src:$ROOT/microservices/router/src${PYTHONPATH:+:$PYTHONPATH}"

# Keep each service test path explicit so a missing or renamed stream fails
# loudly instead of silently reducing coverage.
exec $PYTEST -q \
  "$ROOT/backend/shared/tests" \
  "$ROOT/microservices/auth/tests" \
  "$ROOT/microservices/billing/tests" \
  "$ROOT/microservices/gateway/tests" \
  "$ROOT/microservices/provider/tests" \
  "$ROOT/microservices/router/tests"
