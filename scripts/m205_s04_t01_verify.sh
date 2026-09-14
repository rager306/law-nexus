#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

uv run python scripts/m205_s04_reconciliation.py check
if uv run python scripts/m205_s04_reconciliation.py check --input ../escape.yaml >/dev/null 2>&1; then
  echo "hostile traversal unexpectedly accepted" >&2
  exit 1
fi
if uv run python scripts/m205_s04_reconciliation.py check --input 'prd\\architecture\\m205-s04-docs-reconciliation.yaml' >/dev/null 2>&1; then
  echo "hostile backslash path unexpectedly accepted" >&2
  exit 1
fi

printf '%s\n' "S04_T01_RECONCILIATION_OK" "S04_T01_BOUNDARIES_OK"
