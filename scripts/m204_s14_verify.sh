#!/usr/bin/env bash
# Bounded M204/S14 aggregate. Frozen evidence is never regenerated or rewritten.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s14_evidence_verify.py verify
bash scripts/m204_s14_t01_verify.sh
bash scripts/m204_s14_t02_verify.sh
uv run python scripts/m204_s10_c4_run.py --verify-receipt \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  --historical-binding prd/migration/rust-evidence/m204-s14-s10-source-binding.json
uv run python scripts/m204_s10_battery.py --check --no-gates
uv run python scripts/test_m204_s10_battery.py
bash scripts/m204_s13_t03_verify.sh
uv run python scripts/m204_s14_evidence_verify.py verify
printf '%s\n' S14_VERIFY_OK
