#!/usr/bin/env bash
# Single serialized host proof for M204/S14/T03.
set -euo pipefail
cd "$(dirname "$0")/.."
BEFORE=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl \
  prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json \
  prd/migration/rust-evidence/m204-s11-c4-failed-classification.json \
  prd/migration/rust-evidence/m204-s13-s07-verification-battery.json)
uv run python scripts/m204_s14_evidence_verify.py verify
bash scripts/m204_s14_verify.sh
uv run python scripts/test_m204_s14_evidence_verify.py
uv run python scripts/m204_s14_evidence_verify.py verify
uv run ruff check scripts/m204_s14_evidence_verify.py scripts/test_m204_s14_evidence_verify.py
uv run ruff format --check scripts/m204_s14_evidence_verify.py scripts/test_m204_s14_evidence_verify.py
cargo fmt --all --check
cargo check --workspace --offline
AFTER=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl \
  prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json \
  prd/migration/rust-evidence/m204-s11-c4-failed-classification.json \
  prd/migration/rust-evidence/m204-s13-s07-verification-battery.json)
test "$BEFORE" = "$AFTER"
printf '%s\n' S14_T03_VERIFY_OK
