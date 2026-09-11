#!/usr/bin/env bash
# Host-safe S05 T02 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s05_process_verify.py
uv run ruff check scripts/m204_s05_process_verify.py
uv run ruff format --check scripts/m204_s05_process_verify.py
echo S05_T02_VERIFY_OK
