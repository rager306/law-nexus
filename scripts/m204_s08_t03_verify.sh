#!/usr/bin/env bash
# Host-safe S08 T03 verifier. Single executable, no &&, no nested quotes.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s08_battery.py
echo S08_T03_VERIFY_OK
