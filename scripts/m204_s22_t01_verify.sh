#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
cd "$root"
exec uv run python scripts/m204_s22_liveness.py check \
  --root "$root" \
  --ledger prd/migration/rust-evidence/m204-s22-external-blocker.json \
  --manifest prd/migration/rust-evidence/m204-s22-frozen-hashes.json
