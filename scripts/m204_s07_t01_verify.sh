#!/usr/bin/env bash
# Host-safe S07 T01 verifier. Single executable, no && chaining.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s07_governor_repeat.py
uv run python scripts/m204_s07_governor_repeat.py --check
uv run python scripts/m204_s06_governor_evidence.py --check
echo S07_T01_VERIFY_OK
