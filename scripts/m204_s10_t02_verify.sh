#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s10_c4_run.py
uv run ruff check scripts/m204_s10_c4_run.py scripts/test_m204_s10_c4_run.py
uv run python -m py_compile scripts/m204_s10_c4_run.py scripts/test_m204_s10_c4_run.py
printf '%s\n' 'M204 S10 T02 VERIFY OK'
