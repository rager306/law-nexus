#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python scripts/m204_s10_calibrate.py --verify
