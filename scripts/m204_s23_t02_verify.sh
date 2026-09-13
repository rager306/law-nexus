#!/usr/bin/env bash
# Bounded S23 T02 hostile subprocess proof; no corpus walk is launched.
set -euo pipefail
cd "$(dirname "$0")/.."

before=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl \
  prd/migration/rust-evidence/m204-s14-s10-source-binding.json \
  prd/migration/rust-evidence/m204-s22-external-blocker.json \
  prd/migration/rust-evidence/m204-s22-frozen-hashes.json)

uv run python scripts/test_m204_s23_c4_run.py
uv run python scripts/test_m204_s10_c4_run.py
uv run python scripts/test_m204_s14_source_binding.py
uv run python scripts/m204_s14_source_binding.py verify
bash scripts/m204_s22_t01_verify.sh

# The frozen historical S10 consumer must fail closed under its real CLI: its
# binary pin is intentionally historical and must not be refreshed by T02.
if uv run python scripts/m204_s10_c4_run.py \
  --verify-receipt prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  > /tmp/m204-s23-s10.stdout 2> /tmp/m204-s23-s10.stderr; then
  echo 'historical S10 receipt unexpectedly verified against current binary' >&2
  exit 1
fi
grep -q 'binary hash binding mismatch' /tmp/m204-s23-s10.stderr
if uv run python scripts/m204_s10_c4_run.py \
  --verify-receipt prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  --require-operational-pass; then
  echo 'historical S10 receipt unexpectedly passed operational gate' >&2
  exit 1
fi

after=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl \
  prd/migration/rust-evidence/m204-s14-s10-source-binding.json \
  prd/migration/rust-evidence/m204-s22-external-blocker.json \
  prd/migration/rust-evidence/m204-s22-frozen-hashes.json)
test "$before" = "$after"

uv run ruff check scripts/test_m204_s23_c4_run.py
uv run ruff format --check scripts/test_m204_s23_c4_run.py
printf '%s\n' S23_T02_SUBPROCESS_OK S23_T02_HISTORICAL_BYTES_OK S23_T02_VERIFY_OK
