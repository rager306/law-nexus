#!/usr/bin/env bash
# Host-safe S06 T04 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s06_evidence_verify.py
bash scripts/m204_s06_verify.sh
echo S06_T04_VERIFY_OK
