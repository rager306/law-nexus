#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for path in \
  scripts/m204_s23_liveness.py \
  scripts/test_m204_s23_liveness.py \
  prd/migration/rust-evidence/m204-s23-external-blocker.json \
  prd/migration/rust-evidence/m204-s23-frozen-hashes.json; do
  test -f "$path"
done

uv run python scripts/m204_s23_liveness.py check
uv run python -m unittest scripts/test_m204_s23_liveness.py
printf '%s\n' S23_T03_VERIFY_OK
