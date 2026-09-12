#!/usr/bin/env bash
# Tracked aggregate S08 integrity verifier. Single executable, no corpus walk.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s08_source_revision.py
source_revision="$(node scripts/m204_s08_source_revision.mjs | uv run python -c 'import json, sys; print(json.load(sys.stdin)["source_revision"])')"
printf 'S08_SOURCE_REVISION=%s\n' "$source_revision"
uv run python scripts/test_m204_s08_battery.py
uv run python scripts/m204_s08_battery.py --check
bash scripts/m204_s07_verify.sh
uv run ruff format --check scripts/m204_s08_battery.py scripts/test_m204_s08_battery.py scripts/test_m204_s08_source_revision.py
uv run ruff check scripts/m204_s08_battery.py scripts/test_m204_s08_battery.py scripts/test_m204_s08_source_revision.py
cargo fmt --all --check
cargo check --workspace --offline
uv run python scripts/m204_s08_battery.py --check
printf '%s\n' S08_VERIFY_OK
