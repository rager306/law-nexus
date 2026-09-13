#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

census=prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json
manifest=prd/migration/rust-evidence/m204-s21-frozen-hashes.json
checker=scripts/m204_s21_loop_note.py
adversarial=scripts/test_m204_s21_validate_loop.py
review=doc/review/review-28.md
runbook=doc/gsd-headless-supervisor.md

# T03 is a fixed-census verifier: it never composes or replaces tracked evidence.
test -f "$census"
test -f "$manifest"
test -f "$checker"
test -f "$adversarial"
test -f "$review"
test -f "$runbook"

pins=(
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json
  prd/migration/rust-evidence/m204-s09-trigger-sql.json
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json
  prd/migration/rust-evidence/m204-s15-requirement-class.json
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json
  prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json
  prd/migration/rust-evidence/m204-s16-frozen-hashes.json
  prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json
  prd/migration/rust-evidence/m204-s17-frozen-hashes.json
  prd/migration/rust-evidence/m204-s18-post-s17-validate-loop.json
  prd/migration/rust-evidence/m204-s18-frozen-hashes.json
  prd/migration/rust-evidence/m204-s19-post-s18-validate-abort.json
  prd/migration/rust-evidence/m204-s19-frozen-hashes.json
  prd/migration/rust-evidence/m204-s20-post-s19-validate-loop.json
  prd/migration/rust-evidence/m204-s20-frozen-hashes.json
)
test "${#pins[@]}" -eq 16

# Capture every immutable input before any subprocess; any mutation is fatal.
before=$(sha256sum "$census" "$manifest" "${pins[@]}")

uv run python scripts/m204_s21_loop_note.py check --root "$PWD" --census "$PWD/$census" --manifest "$PWD/$manifest"
uv run python -m unittest scripts/test_m204_s21_validate_loop.py

# Independent consumer assertions: do not derive these counts from the checker.
uv run python - "$census" "$manifest" "$review" "$runbook" "${pins[@]}" <<'PY'
import json
import sys
from pathlib import Path

census = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
review = Path(sys.argv[3]).read_text(encoding="utf-8")
runbook = Path(sys.argv[4]).read_text(encoding="utf-8")
pins = [Path(value).as_posix() for value in sys.argv[5:]]

assert census["dispatch_count"] == 4
assert census["abort_count"] == 2
assert census["cancelled_count"] == 2
assert len(census["aborts"]) == 2
assert len(census["cancelled"]) == 2
assert all(row["unit_type"] == "validate-milestone" for row in census["aborts"] + census["cancelled"])
assert all(row["unit_start_at"] for row in census["aborts"] + census["cancelled"])
assert all(row["journal_unit_start_present"] is True for row in census["cancelled"])
assert all("finalize_status" not in row for row in census["cancelled"])
assert all(row["error_message"] == "Provider error: Connection error." for row in census["cancelled"])
assert census["supervisor_exit"]["exit_reason"] == "closeout-break"
assert census["supervisor_exit"]["headless_pid"] == "1841192"
assert census["supervisor_exit"]["closeout_n"] == 0
assert census["engine_fix"] == "not_fixed"
assert census["law_nexus_fixable"] is False
assert census["c4_acceptance"] == "non-pass"
assert census["retry_substitute"] is False
assert manifest["schema"] == "law-nexus/m204-s21-frozen-hashes/v1"
assert [entry["path"] for entry in manifest["files"]] == pins
assert len(manifest["files"]) == 16

for text in (review, runbook):
    for anchor in ("four validate dispatches", "two no-artifact", "two journal-cancelled", "toolCalls=0", "closeout-break", "1841192", "engine_fix=not_fixed", "law_nexus_fixable=false", "C4", "retry substitute"):
        assert anchor in text, anchor
    assert "STOP after four retries is not an additional abort" in text or "STOP message after four retries is not an additional abort" in text
    assert "Provider error: Connection error." in text
    assert "not attributed" in text or "not attributed to" in text

assert "validate-milestone" in review and "not an automatic retry substitute" in review
print("S21_T03_INDEPENDENT_ASSERTIONS_OK")
PY

after=$(sha256sum "$census" "$manifest" "${pins[@]}")
test "$before" = "$after"
printf '%s\n' S21_T03_VERIFY_OK
