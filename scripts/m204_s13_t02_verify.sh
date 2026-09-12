#!/usr/bin/env bash
# Host-safe S13/T02 replay and frozen-battery verifier.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/m204_s13_t01_verify.sh
uv run python scripts/test_m204_s07_c4_run.py
uv run python scripts/test_m204_s07_evidence_verify.py
uv run python scripts/test_m204_s13_source_binding.py
uv run python scripts/m204_s07_c4_run.py --verify-historical \
  prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json \
  --pinned-receipt prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json
uv run python scripts/m204_s07_c4_run.py --verify-historical \
  prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json \
  --pinned-receipt prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json
uv run python scripts/m204_s07_evidence_verify.py --check --write-battery
uv run python scripts/m204_s07_evidence_verify.py --check --write-battery
uv run ruff check scripts/m204_s07_c4_run.py scripts/m204_s07_evidence_verify.py scripts/m204_s13_source_binding.py scripts/test_m204_s07_c4_run.py scripts/test_m204_s07_evidence_verify.py scripts/test_m204_s13_source_binding.py
uv run ruff format --check scripts/m204_s07_c4_run.py scripts/m204_s07_evidence_verify.py scripts/m204_s13_source_binding.py scripts/test_m204_s07_c4_run.py scripts/test_m204_s07_evidence_verify.py scripts/test_m204_s13_source_binding.py
printf '%s\n' S13_T02_REPLAY_OK
