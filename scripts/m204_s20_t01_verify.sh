#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s20-post-s19-validate-loop.json
manifest=prd/migration/rust-evidence/m204-s20-frozen-hashes.json
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
)
before=$(sha256sum "${pins[@]}")
uv run python scripts/m204_s20_loop_note.py compose
uv run python scripts/m204_s20_loop_note.py check
uv run python - "$artifact" "$manifest" <<'PY'
import json
import sys
from pathlib import Path
artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert len(artifact["aborts"]) == 4
assert [row["flow_id"] for row in artifact["aborts"]] == [
    "041c0f6f-bdee-4e84-91d2-b8299cde3d0c",
    "ffe37bd6-6432-4f70-a1eb-f35f376cf47e",
    "e82c0df7-693b-4110-8fe8-e52cafc21c83",
    "2bd6591f-0180-4351-8cae-32425d1e20a2",
]
assert artifact["supervisor_exit"]["headless_pid"] == "1332614"
assert artifact["supervisor_exit"]["tool_calls"] == 7
assert artifact["supervisor_exit"]["journal_unit_start_present"] is True
assert artifact["supervisor_exit"]["exit_reason"] == "closeout-break"
assert artifact["supervisor_exit"]["closeout_n"] == 0
assert "intercept" not in artifact and "crash_restart" not in artifact
assert artifact["law_nexus_fixable"] is False
assert artifact["s20_called_validate_milestone"] is False
assert artifact["validation_projection_present"] is False
assert artifact["s19_census_stopped_dispatch"] is False
assert artifact["retry_substitute"] is False
assert manifest["schema"] == "law-nexus/m204-s20-frozen-hashes/v1"
assert len(manifest["files"]) == 14
assert all(set(x) == {"path", "sha256", "size_bytes"} for x in manifest["files"])
assert artifact["frozen_manifest"]["path"] == "prd/migration/rust-evidence/m204-s20-frozen-hashes.json"
print("S20_T01_EXACT_RECORDS_OK")
PY
after=$(sha256sum "${pins[@]}")
test "$before" = "$after"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/prd/migration/rust-evidence"
for path in "${pins[@]}"; do cp "$path" "$tmp/$path"; done
cp "$artifact" "$tmp/$artifact"
cp "$manifest" "$tmp/$manifest"
cp scripts/m204_s20_loop_note.py "$tmp/m204_s20_loop_note.py"
printf 'tamper\n' >> "$tmp/prd/migration/rust-evidence/m204-s18-frozen-hashes.json"
if uv run python scripts/m204_s20_loop_note.py check --root "$tmp" --census "$tmp/$artifact" --manifest "$tmp/$manifest"; then
  echo 'drift unexpectedly accepted' >&2
  exit 1
fi
printf '%s\n' S20_T01_CENSUS_OK
