#!/usr/bin/env bash
# Tracked aggregate S08 integrity verifier. Single executable, no corpus walk.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s08_source_revision.py
node scripts/m204_s08_source_revision.mjs
uv run python scripts/test_m204_s08_battery.py
uv run python scripts/m204_s08_battery.py --check
bash scripts/m204_s07_verify.sh
printf '%s\n' S08_VERIFY_OK
