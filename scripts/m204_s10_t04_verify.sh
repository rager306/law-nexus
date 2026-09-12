#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run pytest -q scripts/test_m204_s10_battery.py
uv run ruff check scripts/m204_s10_battery.py scripts/test_m204_s10_battery.py
uv run python -m py_compile scripts/m204_s10_battery.py scripts/test_m204_s10_battery.py
uv run python scripts/m204_s10_battery.py --check --no-gates
printf '%s\n' 'M204 S10 T04 VERIFY OK'
