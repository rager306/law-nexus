#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pins=(
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json
  prd/migration/rust-evidence/m204-s09-trigger-sql.json
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json
  prd/migration/rust-evidence/m204-s15-requirement-class.json
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json
  prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json
  prd/migration/rust-evidence/m204-s16-frozen-hashes.json
  prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json
  prd/migration/rust-evidence/m204-s17-frozen-hashes.json
)
before=$(sha256sum "${pins[@]}")
bash scripts/m204_s18_t01_verify.sh
bash scripts/m204_s18_t02_verify.sh
bash scripts/m204_s18_verify.sh
uv run ruff format --check scripts/m204_s18_evidence_verify.py scripts/test_m204_s18_evidence_verify.py
uv run ruff check scripts/m204_s18_evidence_verify.py scripts/test_m204_s18_evidence_verify.py
cargo fmt --all --check
cargo check --workspace --offline
after=$(sha256sum "${pins[@]}")
test "$before" = "$after"
printf '%s\n' S18_T03_VERIFY_OK
