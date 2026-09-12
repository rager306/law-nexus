#!/usr/bin/env bash
# Host-safe S08 T02 verifier. Single executable, no &&, no nested quotes.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s08_battery.py --check --write
echo S08_T02_VERIFY_OK
