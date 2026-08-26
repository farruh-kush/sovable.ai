#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTEST="${PYTEST_BIN:-$ROOT/venv/bin/pytest}"
if [[ ! -x "$PYTEST" ]]; then PYTEST="${PYTEST_BIN:-pytest}"; fi
export PYTHONPATH="$ROOT/backend/shared/src:$ROOT/microservices/auth/src:$ROOT/microservices/billing/src:$ROOT/microservices/gateway/src:$ROOT/microservices/provider/src:$ROOT/microservices/router/src"
mkdir -p "$ROOT/testing/evidence"
"$PYTEST" -c "$ROOT/testing/pytest.ini" -q \
  backend/shared/tests \
  microservices/auth/tests \
  microservices/billing/tests \
  microservices/gateway/tests \
  microservices/provider/tests \
  microservices/router/tests \
  testing/platform_tests \
  -m 'not staging' \
  --junitxml="$ROOT/testing/evidence/platform-junit.xml"
