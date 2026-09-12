#!/usr/bin/env bash
# Host-safe S09 T02 verifier. Single executable, no &&, no nested quotes.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s09_validate_deadlock.py
echo S09_T02_VERIFY_OK
