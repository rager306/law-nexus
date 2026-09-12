#!/usr/bin/env bash
# Host-safe S07 T06 verifier. Single command, no nested quotes, no &&.
# Restored aggregate integrity is required. Operational pass is a
# separate receipt claim, not a host-verify floor.
set -euo pipefail
cd "$(dirname "$0")/.."
test -x scripts/m204_s07_verify.sh
bash scripts/m204_s07_verify.sh
RECEIPT=prd/migration/rust-evidence/m204-s07-c4-operational-receipt-passing.json
if [[ -f "$RECEIPT" ]]; then
  uv run python scripts/m204_s07_c4_run.py --verify-receipt "$RECEIPT"
fi
echo S07_T06_VERIFY_OK
