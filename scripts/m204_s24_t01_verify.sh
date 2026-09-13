#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
cd "$root"

uv run python scripts/m204_s24_liveness.py check \
  --root "$root" \
  --packet prd/migration/rust-evidence/m204-s24-criterion-resolution.json \
  --manifest prd/migration/rust-evidence/m204-s24-frozen-hashes.json
printf '%s\n' 'S24_T01_C4_PASS_CITATION_OK'
printf '%s\n' 'S24_T01_HISTORICAL_NON_PASS_OK'

# The source-bound census guard remains empty: S24 does not add engine or
# validation-source files to the product tree.
if git ls-files | rg -q 'milestone-validation|technical\.verdict|trg_workflow|db-milestone-validation'; then
  echo 'S24_T01_FAIL: tracked engine/validation source appeared' >&2
  exit 1
fi
printf '%s\n' 'S24_T01_NO_ENGINE_SOURCE_OK'
