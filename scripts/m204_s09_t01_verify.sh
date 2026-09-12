#!/usr/bin/env bash
# Host-safe S09 T01 verifier. Single executable, no &&, no nested quotes.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s09_deadlock_note.py --check
echo S09_T01_VERIFY_OK
