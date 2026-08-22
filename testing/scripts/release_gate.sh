#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$ROOT/backend/shared/src:$ROOT/microservices/auth/src:$ROOT/microservices/billing/src:$ROOT/microservices/gateway/src:$ROOT/microservices/provider/src:$ROOT/microservices/router/src${PYTHONPATH:+:$PYTHONPATH}"

printf '%s\n' '== Solvable AI whole-platform release gate =='
printf 'Commit: '; git -C "$ROOT" rev-parse --short HEAD

printf '%s\n' '--- repository hygiene ---'
git -C "$ROOT" diff --check
"$PYTHON_BIN" "$ROOT/testing/scripts/secret_scan.py"

printf '%s\n' '--- configuration consistency ---'
if ! cmp -s "$ROOT/ai/config/routing.yaml" "$ROOT/infrastructure/k8s/base/routing.yaml"; then
  echo 'Routing catalog drift detected between ai/config and the Kubernetes ConfigMap source.' >&2
  exit 1
fi

printf '%s\n' '--- Python compilation ---'
"$PYTHON_BIN" -m compileall -q "$ROOT/backend/shared/src" "$ROOT/microservices"

printf '%s\n' '--- backend tests ---'
"$ROOT/testing/scripts/run_tests.sh"

printf '%s\n' '--- frontend checks ---'
if command -v npm >/dev/null 2>&1 && [[ -f "$ROOT/frontend/dashboard/package-lock.json" ]]; then
  (cd "$ROOT/frontend/dashboard" && npm ci --ignore-scripts && npm run typecheck && npm run lint && npm run build)
else
  echo 'npm and the dashboard lockfile are required for the frontend release gate.' >&2
  exit 1
fi

printf '%s\n' '--- Kubernetes render checks ---'
if command -v kustomize >/dev/null 2>&1; then
  KUSTOMIZE_BIN="$(command -v kustomize)"
  render_kustomize() { "$KUSTOMIZE_BIN" build "$1"; }
elif command -v kubectl >/dev/null 2>&1; then
  render_kustomize() { kubectl kustomize "$1"; }
else
  echo 'A working kustomize or kubectl renderer is required for Kubernetes release-gate validation.' >&2
  exit 1
fi
for overlay in alibaba aws; do
    output="$(mktemp)"
    trap 'rm -f "$output"' EXIT
    render_kustomize "$ROOT/infrastructure/k8s/overlays/$overlay" >"$output"
    grep -q '^kind: Deployment$' "$output"
    grep -q '^kind: Service$' "$output"
    rm -f "$output"
    trap - EXIT
    echo "$overlay overlay rendered successfully."
done

printf '%s\n' 'Release gate passed.'
