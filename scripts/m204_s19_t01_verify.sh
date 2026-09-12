#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s19-post-s18-validate-abort.json
manifest=prd/migration/rust-evidence/m204-s19-frozen-hashes.json
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
)
before=$(sha256sum "${pins[@]}")
uv run python scripts/m204_s19_loop_note.py compose
uv run python scripts/m204_s19_loop_note.py check
uv run python - "$artifact" "$manifest" <<'PY'
import json
import sys
from pathlib import Path
artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert set(artifact) == {
    "schema", "milestone", "slice", "predecessor_slice", "s18_complete_at",
    "s18_uat_end_at", "abort_count", "aborts", "supervisor_exit",
    "sql_abort_message", "trigger_name", "engine_fix", "upstream_issue",
    "law_nexus_fixable", "s19_called_validate_milestone",
    "validation_projection_present", "c4_acceptance", "classification",
    "status_effect", "same_defect_as_s09", "s12_hard_block_stopped_dispatch",
    "s16_census_stopped_dispatch", "s17_census_stopped_dispatch",
    "s18_census_stopped_dispatch", "retry_substitute", "frozen_manifest",
}
assert artifact["schema"] == "law-nexus/gsd-post-s18-validate-abort/v1"
assert artifact["slice"] == "S19" and artifact["predecessor_slice"] == "S18"
assert artifact["abort_count"] == 1 and len(artifact["aborts"]) == 1
assert artifact["aborts"][0]["flow_id"] == "38a570c5-47c3-4fcb-af6f-45372aadcf26"
assert artifact["aborts"][0]["unit_end_status"] == "no-artifact"
assert artifact["supervisor_exit"]["classify_status"] == "blocked"
assert artifact["supervisor_exit"]["interrupted"] is False
assert artifact["supervisor_exit"]["journal_unit_start_present"] is True
assert artifact["supervisor_exit"]["tool_calls"] == 62
assert artifact["supervisor_exit"]["headless_pid"] == "1175128"
assert artifact["supervisor_exit"]["exit_reason"] == "closeout-break"
assert artifact["supervisor_exit"]["closeout_n"] == 0
assert "intercept" not in artifact
assert artifact["law_nexus_fixable"] is False
assert artifact["s19_called_validate_milestone"] is False
assert artifact["validation_projection_present"] is False
assert artifact["s18_census_stopped_dispatch"] is False
assert artifact["retry_substitute"] is False
assert artifact["sql_abort_message"] == "technical verdict requires the current criterion and matching settled attempt"
assert manifest["schema"] == "law-nexus/m204-s19-frozen-hashes/v1"
assert len(manifest["files"]) == 12
assert all(set(x) == {"path", "sha256", "size_bytes"} for x in manifest["files"])
assert artifact["frozen_manifest"]["path"] == "prd/migration/rust-evidence/m204-s19-frozen-hashes.json"
print("S19_T01_EXACT_RECORDS_OK")
PY
after=$(sha256sum "${pins[@]}")
test "$before" = "$after"
# Exercise check against a bounded copied root and prove predecessor drift fails closed.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/prd/migration/rust-evidence"
for path in "${pins[@]}"; do cp "$path" "$tmp/$path"; done
cp "$artifact" "$tmp/$artifact"
cp "$manifest" "$tmp/$manifest"
cp scripts/m204_s19_loop_note.py "$tmp/m204_s19_loop_note.py"
printf 'tamper\n' >> "$tmp/prd/migration/rust-evidence/m204-s18-frozen-hashes.json"
if uv run python scripts/m204_s19_loop_note.py check --root "$tmp" --census "$tmp/$artifact" --manifest "$tmp/$manifest"; then
  echo 'drift unexpectedly accepted' >&2
  exit 1
fi
printf '%s\n' S19_T01_CENSUS_OK
