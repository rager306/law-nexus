#!/usr/bin/env bash
# Host-safe S07 T05 verifier. Single command, no nested quotes, no &&.
# Integrity of the eligible receipt is required. Operational pass is a
# separate receipt claim, not a host-verify floor.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s07_c4_run.py --verify-receipt prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json
echo S07_T05_VERIFY_OK
