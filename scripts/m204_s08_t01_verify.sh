#!/usr/bin/env bash
# Host-safe S08 T01 verifier. Single executable, no &&, no nested quotes.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/test_m204_s08_source_revision.py
node scripts/m204_s08_source_revision.mjs
echo S08_T01_VERIFY_OK
