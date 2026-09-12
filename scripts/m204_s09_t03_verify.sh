#!/usr/bin/env bash
# Host-safe S09 T03 verifier. Single executable, no &&, no nested quotes.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/m204_s09_verify.sh
echo S09_T03_VERIFY_OK
