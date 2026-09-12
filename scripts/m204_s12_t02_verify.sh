#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

uv run ruff check scripts/m204_s12_failure_probe.py scripts/test_m204_s12_failure_probe.py
uv run ruff format --check scripts/m204_s12_failure_probe.py scripts/test_m204_s12_failure_probe.py
uv run python scripts/test_m204_s12_failure_probe.py
uv run python scripts/m204_s12_failure_probe.py verify
printf '%s\n' S12_T02_OK
