#!/usr/bin/env bash
# Host-safe S06 T02 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s06_c4_run.py
uv run python scripts/m204_s06_c4_run.py --verify-receipt prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json
echo S06_T02_VERIFY_OK
