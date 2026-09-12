#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json
manifest=prd/migration/rust-evidence/m204-s17-frozen-hashes.json
before=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json \
  prd/migration/rust-evidence/m204-s16-frozen-hashes.json)
uv run python scripts/m204_s17_loop_note.py compose
uv run python scripts/m204_s17_loop_note.py check
uv run python - "$artifact" "$manifest" <<'PY'
import json
import sys
from pathlib import Path

artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert set(artifact) == {
    "schema", "milestone", "slice", "predecessor_slice", "s16_complete_at",
    "s16_uat_end_at", "abort_count", "aborts", "intercept", "sql_abort_message",
    "trigger_name", "engine_fix", "upstream_issue", "law_nexus_fixable",
    "s17_called_validate_milestone", "validation_projection_present", "c4_acceptance",
    "classification", "status_effect", "same_defect_as_s09",
    "s12_hard_block_stopped_dispatch", "s16_census_stopped_dispatch",
    "retry_substitute", "frozen_manifest",
}
assert artifact["schema"] == "law-nexus/gsd-post-s16-validate-loop/v1"
assert artifact["milestone"] == "M204-w2ktfw"
assert artifact["slice"] == "S17"
assert artifact["predecessor_slice"] == "S16"
assert artifact["abort_count"] == 2
assert len(artifact["aborts"]) == 2
assert all(row["unit_end_status"] == "no-artifact" for row in artifact["aborts"])
assert all(row["finalize_status"] == "retry" for row in artifact["aborts"])
assert artifact["intercept"]["kind"] == "predispatch_cancelled_interrupted"
assert artifact["intercept"]["classify_status"] == "cancelled"
assert artifact["intercept"]["interrupted"] is True
assert artifact["intercept"]["tool_calls"] == 0
assert artifact["intercept"]["journal_unit_start_present"] is False
assert isinstance(artifact["intercept"]["headless_pid"], str)
assert artifact["law_nexus_fixable"] is False
assert artifact["s17_called_validate_milestone"] is False
assert artifact["validation_projection_present"] is False
assert artifact["same_defect_as_s09"] is True
assert artifact["retry_substitute"] is False
assert artifact["c4_acceptance"] == "non-pass"
assert artifact["classification"] == "supporting-only"
assert artifact["status_effect"] == "unchanged"
assert manifest["schema"] == "law-nexus/m204-s17-frozen-hashes/v1"
assert len(manifest["files"]) == 8
assert all(set(row) == {"path", "sha256", "size_bytes"} for row in manifest["files"])
assert artifact["frozen_manifest"]["path"] == "prd/migration/rust-evidence/m204-s17-frozen-hashes.json"
print("S17_T01_EXACT_RECORDS_OK")
PY
after=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json \
  prd/migration/rust-evidence/m204-s16-frozen-hashes.json)
test "$before" = "$after"
printf '%s\n' S17_T01_CENSUS_OK
