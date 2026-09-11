#!/usr/bin/env bash
# Host-safe S07 T02 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s07_c4_run.py
uv run python scripts/test_m204_s06_c4_run.py
uv run ruff check scripts/m204_s07_c4_run.py scripts/test_m204_s07_c4_run.py
echo S07_T02_VERIFY_OK
