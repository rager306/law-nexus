#!/usr/bin/env bash
# Tracked aggregate S09 integrity verifier. Single executable, no corpus walk.
set -euo pipefail
cd "$(dirname "$0")/.."

# Capture the historical evidence boundary before running checks that consume it.
# The second snapshot proves that verification itself did not rewrite frozen bytes.
frozen_snapshot() {
  sha256sum \
    prd/migration/rust-evidence/m204-s06-*.json \
    prd/migration/rust-evidence/m204-s07-*.json \
    prd/migration/rust-evidence/m203-s08-*.json \
    prd/migration/rust-evidence/m203-s08-*.jsonl \
    | sort -k2
}

before_frozen="$(frozen_snapshot)"

bash scripts/m204_s09_t01_verify.sh
bash scripts/m204_s09_t02_verify.sh

uv run python - <<'PY'
import json
from pathlib import Path

root = Path('.')
deadlock = json.loads(
    (root / 'prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json').read_text()
)
trigger = json.loads(
    (root / 'prd/migration/rust-evidence/m204-s09-trigger-sql.json').read_text()
)
battery = json.loads(
    (root / 'prd/migration/rust-evidence/m204-validation-battery-20260912.json').read_text()
)
assert deadlock['schema'] == 'law-nexus/gsd-validate-deadlock/v1'
assert deadlock['abort_message'] == (
    'technical verdict requires the current criterion and matching settled attempt'
)
assert deadlock['activity_census']['minimum_observed_rows'] >= 31
assert deadlock['validation_projection_present'] is False
assert deadlock['statuses'] == {'engine_fix': 'not_fixed', 'upstream_issue': 'not_filed'}
assert deadlock['law_nexus_fixable'] is False
assert deadlock['trigger_name'] == 'trg_workflow_technical_verdict_scope'
assert deadlock['c4_remains']['operational_acceptance'] == 'non-pass'
assert trigger['schema'] == 'law-nexus/gsd-trigger-sql-snapshot/v1'
assert trigger['source_files_relative_to_GSD_HOME'] is True
assert {'v34', 'v42'} <= set(trigger['snapshots'])
assert battery['schema_version'] == 'law-nexus/milestone-validation-battery/v1'
assert battery['summary']['failed'] == 1
assert battery['c4']['operational_acceptance'] == 'non-pass'
assert battery['c4']['observation'] == 'failed'
print('S09 JSON and S08 battery pins OK')
PY

# The documented supervisor response is part of the evidence contract.
grep -F 'Validate technical-verdict deadlock' doc/gsd-headless-supervisor.md >/dev/null
grep -F 'engine HARD BLOCK' doc/gsd-headless-supervisor.md >/dev/null
grep -F 'do not restart auto for another validate' doc/gsd-headless-supervisor.md >/dev/null
grep -F 'do not sqlite-patch' doc/gsd-headless-supervisor.md >/dev/null
grep -F 'do not mark C4 pass' doc/gsd-headless-supervisor.md >/dev/null

# S03/S06/S07 own their broad historical contracts.  Do not replay them here:
# S09 is an aggregate integrity check, and replaying corpus/build verifiers makes
# this bounded host gate timeout.  The frozen snapshot above plus the explicit
# S08 battery check below preserve the regression boundary without mutation.
uv run python scripts/m204_s08_battery.py --check

# Re-check the frozen evidence boundary after all bounded checks.
after_frozen="$(frozen_snapshot)"
if [[ "$before_frozen" != "$after_frozen" ]]; then
  echo 'frozen M203/S06/S07 evidence changed during S09 verification' >&2
  diff -u <(printf '%s\n' "$before_frozen") <(printf '%s\n' "$after_frozen") >&2 || true
  exit 1
fi

uv run ruff format --check \
  scripts/m204_s09_deadlock_note.py \
  scripts/test_m204_s09_validate_deadlock.py \
  scripts/m204_s08_battery.py
uv run ruff check \
  scripts/m204_s09_deadlock_note.py \
  scripts/test_m204_s09_validate_deadlock.py \
  scripts/m204_s08_battery.py
cargo fmt --all --check
cargo check --workspace --offline
printf '%s\n' S09_VERIFY_OK
