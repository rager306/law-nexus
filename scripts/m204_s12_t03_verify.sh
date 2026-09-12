#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Host entry point: all substantive checks remain bounded in the aggregate.
bash scripts/m204_s12_verify.sh
printf '%s\n' S12_T03_VERIFY_OK
