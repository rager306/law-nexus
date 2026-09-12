#!/usr/bin/env bash
# Tracked aggregate S09 integrity verifier. Single executable, no corpus walk.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s09_deadlock_note.py --check
uv run python scripts/test_m204_s09_validate_deadlock.py
printf '%s\n' S09_VERIFY_OK
