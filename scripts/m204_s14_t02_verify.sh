#!/usr/bin/env bash
# Bounded S14 T02 verification: historical replay is additive and source-bound.
set -euo pipefail
cd "$(dirname "$0")/.."
BEFORE=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl \
  prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json)
uv run python scripts/test_m204_s10_c4_run.py
uv run python scripts/test_m204_s14_source_binding.py
uv run python scripts/m204_s14_source_binding.py verify
uv run python scripts/m204_s10_c4_run.py \
  --verify-receipt prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  --historical-binding prd/migration/rust-evidence/m204-s14-s10-source-binding.json
if uv run python scripts/m204_s10_c4_run.py \
  --verify-receipt prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  --historical-binding prd/migration/rust-evidence/m204-s14-s10-source-binding.json \
  --require-operational-pass; then
  echo "historical replay unexpectedly passed operational gate" >&2
  exit 1
fi
AFTER=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl \
  prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json)
test "$BEFORE" = "$AFTER"
printf '%s\n' S14_T02_REPLAY_OK
