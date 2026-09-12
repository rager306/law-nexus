#!/usr/bin/env bash
# Single serialized host command for the additive S13 closeout evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
BEFORE=$(sha256sum \
  prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json \
  prd/migration/rust-evidence/m204-s07-verification-battery.json)
bash scripts/m204_s13_verify.sh
AFTER=$(sha256sum \
  prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json \
  prd/migration/rust-evidence/m204-s07-verification-battery.json)
test "$BEFORE" = "$AFTER"
printf '%s\n' S13_T03_VERIFY_OK
