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

uv run python scripts/test_m204_s17_validate_loop.py
uv run ruff format --check scripts/m204_s17_loop_note.py scripts/test_m204_s17_validate_loop.py
uv run ruff check scripts/m204_s17_loop_note.py scripts/test_m204_s17_validate_loop.py

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
printf '%s\n' S17_T02_NEGATIVES_OK
