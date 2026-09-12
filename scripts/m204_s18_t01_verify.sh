#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s18-post-s17-validate-loop.json
manifest=prd/migration/rust-evidence/m204-s18-frozen-hashes.json
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
)
before=$(sha256sum "${pins[@]}")
uv run python scripts/m204_s18_loop_note.py compose
uv run python scripts/m204_s18_loop_note.py check
uv run python - "$artifact" "$manifest" <<'PY'
import json
import sys
from pathlib import Path
artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert set(artifact) == {
    "schema", "milestone", "slice", "predecessor_slice", "s17_complete_at",
    "s17_uat_end_at", "abort_count", "aborts", "intercept", "sql_abort_message",
    "trigger_name", "engine_fix", "upstream_issue", "law_nexus_fixable",
    "s18_called_validate_milestone", "validation_projection_present", "c4_acceptance",
    "classification", "status_effect", "same_defect_as_s09",
    "s12_hard_block_stopped_dispatch", "s16_census_stopped_dispatch",
    "s17_census_stopped_dispatch", "retry_substitute", "frozen_manifest",
}
assert artifact["schema"] == "law-nexus/gsd-post-s17-validate-loop/v1"
assert artifact["slice"] == "S18" and artifact["predecessor_slice"] == "S17"
assert artifact["abort_count"] == 2 and len(artifact["aborts"]) == 2
assert all(x["unit_end_status"] == "no-artifact" and x["finalize_status"] == "retry" for x in artifact["aborts"])
assert artifact["intercept"]["classify_status"] == "cancelled"
assert artifact["intercept"]["interrupted"] is True
assert artifact["intercept"]["tool_calls"] == 0
assert artifact["intercept"]["journal_unit_start_present"] is False
assert isinstance(artifact["intercept"]["headless_pid"], str)
assert artifact["law_nexus_fixable"] is False
assert artifact["s18_called_validate_milestone"] is False
assert artifact["validation_projection_present"] is False
assert artifact["s17_census_stopped_dispatch"] is False
assert artifact["same_defect_as_s09"] is True
assert artifact["retry_substitute"] is False
assert artifact["c4_acceptance"] == "non-pass"
assert artifact["classification"] == "supporting-only"
assert artifact["status_effect"] == "unchanged"
assert manifest["schema"] == "law-nexus/m204-s18-frozen-hashes/v1"
assert len(manifest["files"]) == 10
assert all(set(x) == {"path", "sha256", "size_bytes"} for x in manifest["files"])
assert artifact["frozen_manifest"]["path"] == "prd/migration/rust-evidence/m204-s18-frozen-hashes.json"
print("S18_T01_EXACT_RECORDS_OK")
PY
after=$(sha256sum "${pins[@]}")
test "$before" = "$after"

# Exercise the public check boundary against a temporary predecessor root.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/prd/migration/rust-evidence"
for path in "${pins[@]}"; do cp "$path" "$tmp/$path"; done
cp "$artifact" "$tmp/$artifact"
cp "$manifest" "$tmp/$manifest"
cp scripts/m204_s18_loop_note.py "$tmp/m204_s18_loop_note.py"
printf 'tamper\n' >> "$tmp/prd/migration/rust-evidence/m204-s17-frozen-hashes.json"
if uv run python scripts/m204_s18_loop_note.py check --root "$tmp" --census "$tmp/$artifact" --manifest "$tmp/$manifest"; then
  echo 'drift unexpectedly accepted' >&2
  exit 1
fi
printf '%s\n' S18_T01_CENSUS_OK
