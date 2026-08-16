#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTEST="${PYTEST_BIN:-$ROOT/.venv/bin/pytest}"
if [[ ! -x "$PYTEST" ]]; then PYTEST="${PYTEST_BIN:-pytest}"; fi
export PYTHONPATH="$ROOT/shared/src:$ROOT/services/auth/src:$ROOT/services/billing/src:$ROOT/services/gateway/src:$ROOT/services/provider/src:$ROOT/services/router/src"
"$PYTEST" -q shared/tests services/auth/tests services/billing/tests services/gateway/tests services/provider/tests services/router/tests
