#!/usr/bin/env bash
# Serialized M204/S15 aggregate. Never composes or rewrites frozen evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s15_evidence_verify.py verify
bash scripts/m204_s15_t01_verify.sh
bash scripts/m204_s15_t02_verify.sh
printf '%s\n' S15_VERIFY_OK
