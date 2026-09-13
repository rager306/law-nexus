#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

uv run python scripts/m204_s23_battery.py check
uv run python scripts/test_m204_s23_battery.py
uv run ruff check scripts/m204_s23_battery.py scripts/test_m204_s23_battery.py
uv run ruff format --check scripts/m204_s23_battery.py scripts/test_m204_s23_battery.py
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
cargo fmt --all --check
printf '%s\n' S23_T04_VERIFY_OK
