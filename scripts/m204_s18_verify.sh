#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s18_evidence_verify.py verify
printf '%s\n' S18_VERIFY_OK
