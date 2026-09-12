#!/usr/bin/env bash
# Host-safe S08 T04 verifier. Single executable, no &&, no nested quotes.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/m204_s08_verify.sh
echo S08_T04_VERIFY_OK
