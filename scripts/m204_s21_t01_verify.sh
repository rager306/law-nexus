#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json
manifest=prd/migration/rust-evidence/m204-s21-frozen-hashes.json
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
before=$(sha256sum "${pins[@]}")
uv run python scripts/m204_s21_loop_note.py compose
uv run python scripts/m204_s21_loop_note.py check
uv run python - "$artifact" "$manifest" <<'PY'
import json
import sys
from pathlib import Path
artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert artifact["schema"] == "law-nexus/gsd-post-s20-validate-loop/v1"
assert artifact["slice"] == "S21" and artifact["predecessor_slice"] == "S20"
assert artifact["dispatch_count"] == 4
assert artifact["abort_count"] == 2 and len(artifact["aborts"]) == 2
assert [row["flow_id"] for row in artifact["aborts"]] == [
    "061fea44-c911-4578-b952-f123e3cf0319",
    "9f2369bd-5e43-406a-a9bd-555a895bebc6",
]
assert artifact["cancelled_count"] == 2 and len(artifact["cancelled"]) == 2
assert [row["flow_id"] for row in artifact["cancelled"]] == [
    "5c9ed6e5-06e7-4228-ac9a-0b7b9322ac29",
    "581f8dbe-b14f-4426-9b81-0cf5adc41ea4",
]
assert all(row["journal_unit_start_present"] is True for row in artifact["cancelled"])
assert all(row["unit_end_status"] == "cancelled" for row in artifact["cancelled"])
assert all(set(row) == {
    "ordinal", "unit_start_at", "unit_end_at", "unit_end_status",
    "artifact_verified", "error_category", "error_message", "flow_id",
    "unit_id", "unit_type", "journal_unit_start_present",
} for row in artifact["cancelled"])
assert artifact["supervisor_exit"]["headless_pid"] == "1841192"
assert artifact["supervisor_exit"]["tool_calls"] == 0
assert artifact["supervisor_exit"]["classify_status"] == "blocked"
assert artifact["supervisor_exit"]["interrupted"] is False
assert artifact["supervisor_exit"]["exit_reason"] == "closeout-break"
assert artifact["supervisor_exit"]["stop_text"] == "closeout break not recovering after 4 retries (status=blocked)"
assert "intercept" not in artifact
assert artifact["law_nexus_fixable"] is False
assert artifact["engine_fix"] == "not_fixed"
assert artifact["validation_projection_present"] is False
assert artifact["c4_acceptance"] == "non-pass"
assert manifest["schema"] == "law-nexus/m204-s21-frozen-hashes/v1"
assert len(manifest["files"]) == 16
assert all(set(item) == {"path", "sha256", "size_bytes"} for item in manifest["files"])
assert artifact["frozen_manifest"]["path"] == "prd/migration/rust-evidence/m204-s21-frozen-hashes.json"
print("S21_T01_EXACT_RECORDS_OK")
PY
after=$(sha256sum "${pins[@]}")
test "$before" = "$after"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/prd/migration/rust-evidence"
for path in "${pins[@]}"; do cp "$path" "$tmp/$path"; done
cp "$artifact" "$tmp/$artifact"
cp "$manifest" "$tmp/$manifest"
printf 'tamper\n' >> "$tmp/prd/migration/rust-evidence/m204-s20-frozen-hashes.json"
if uv run python scripts/m204_s21_loop_note.py check --root "$tmp" --census "$tmp/$artifact" --manifest "$tmp/$manifest"; then
  echo 'drift unexpectedly accepted' >&2
  exit 1
fi
printf '%s\n' S21_T01_CENSUS_OK
