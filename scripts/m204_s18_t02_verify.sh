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
uv run python scripts/test_m204_s18_validate_loop.py
uv run ruff format --check scripts/m204_s18_loop_note.py scripts/test_m204_s18_validate_loop.py
uv run ruff check scripts/m204_s18_loop_note.py scripts/test_m204_s18_validate_loop.py
after=$(sha256sum "${pins[@]}")
test "$before" = "$after"
printf '%s\n' S18_T02_NEGATIVES_OK
