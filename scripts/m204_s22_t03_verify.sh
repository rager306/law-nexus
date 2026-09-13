#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

battery=prd/migration/rust-evidence/m204-s22-operational-battery.json
stdout=prd/migration/rust-evidence/m204-s22-c4-control.stdout.txt
stderr=prd/migration/rust-evidence/m204-s22-c4-control.stderr.txt
for path in "$battery" "$stdout" "$stderr" scripts/m204_s22_battery.py scripts/m204_s22_liveness.py scripts/test_m204_s22_liveness.py doc/review/review-28.md doc/gsd-headless-supervisor.md; do
  test -f "$path"
done
exec uv run python scripts/m204_s22_battery.py check
