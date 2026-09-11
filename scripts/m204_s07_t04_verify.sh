#!/usr/bin/env bash
# Host-safe S07 T04 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/m204_s07_verify.sh
uv run python scripts/m204_s07_evidence_verify.py --check --require-operational-pass
echo S07_T04_VERIFY_OK
