#!/usr/bin/env bash
# Single serialized host proof for M204/S15/T03.
set -euo pipefail
cd "$(dirname "$0")/.."
SOURCES=(
  prd/migration/rust-evidence/m204-s06-requirement-evidence.json
  prd/migration/rust-evidence/m204-s07-requirement-evidence.json
  prd/migration/rust-evidence/m204-s10-requirement-evidence.json
  prd/migration/rust-evidence/m204-s14-c4-acceptance.json
  prd/migration/rust-evidence/m204-s14-frozen-hashes.json
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json
  prd/migration/rust-evidence/m204-s15-requirement-class.json
)
BEFORE=$(sha256sum "${SOURCES[@]}")
bash scripts/m204_s15_verify.sh
uv run python scripts/test_m204_s15_evidence_verify.py
uv run python scripts/m204_s15_evidence_verify.py verify
uv run ruff check scripts/m204_s15_evidence_verify.py scripts/test_m204_s15_evidence_verify.py
uv run ruff format --check scripts/m204_s15_evidence_verify.py scripts/test_m204_s15_evidence_verify.py
cargo fmt --all --check
cargo check --workspace --offline
AFTER=$(sha256sum "${SOURCES[@]}")
test "$BEFORE" = "$AFTER"
printf '%s\n' S15_T03_VERIFY_OK
