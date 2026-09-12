#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

before=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json \
  prd/migration/rust-evidence/m204-s16-frozen-hashes.json)

uv run python scripts/test_m204_s17_evidence_verify.py
bash scripts/m204_s17_verify.sh
uv run ruff format scripts/m204_s17_evidence_verify.py scripts/test_m204_s17_evidence_verify.py
uv run ruff check scripts/m204_s17_evidence_verify.py scripts/test_m204_s17_evidence_verify.py
cargo fmt --all --check
cargo check --workspace --offline

after=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json \
  prd/migration/rust-evidence/m204-s16-frozen-hashes.json)
test "$before" = "$after"
printf '%s\n' S17_T03_VERIFY_OK
