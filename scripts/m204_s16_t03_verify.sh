#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

before=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json)

bash scripts/m204_s16_verify.sh
uv run python scripts/test_m204_s16_validate_loop.py
uv run python scripts/test_m204_s16_evidence_verify.py
uv run ruff check scripts/m204_s16_evidence_verify.py scripts/test_m204_s16_evidence_verify.py
uv run ruff format --check scripts/m204_s16_evidence_verify.py scripts/test_m204_s16_evidence_verify.py
cargo fmt --all --check
cargo check --workspace --offline

after=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json)
test "$before" = "$after"
printf '%s\n' S16_T03_VERIFY_OK
