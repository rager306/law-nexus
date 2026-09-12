#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json
manifest=prd/migration/rust-evidence/m204-s16-frozen-hashes.json
before=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json)
uv run python scripts/m204_s16_loop_note.py compose
uv run python scripts/m204_s16_loop_note.py check
uv run python - "$artifact" "$manifest" <<'PY'
import json
import sys
from pathlib import Path

artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert artifact["schema"] == "law-nexus/gsd-post-s15-validate-loop/v1"
assert artifact["milestone"] == "M204-w2ktfw"
assert artifact["slice"] == "S16"
assert artifact["predecessor_slice"] == "S15"
assert artifact["abort_count"] == 3
assert len(artifact["aborts"]) == 3
assert all(row["unit_end_status"] == "no-artifact" for row in artifact["aborts"])
assert all(row["finalize_status"] == "retry" for row in artifact["aborts"])
assert artifact["law_nexus_fixable"] is False
assert artifact["s16_called_validate_milestone"] is False
assert artifact["validation_projection_present"] is False
assert artifact["same_defect_as_s09"] is True
assert artifact["retry_substitute"] is False
assert manifest["schema"] == "law-nexus/m204-s16-frozen-hashes/v1"
assert len(manifest["files"]) == 6
assert all(set(row) == {"path", "sha256", "size_bytes"} for row in manifest["files"])
print("S16_T01_EXACT_RECORDS_OK")
PY
after=$(sha256sum \
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json \
  prd/migration/rust-evidence/m204-s09-trigger-sql.json \
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json \
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json \
  prd/migration/rust-evidence/m204-s15-requirement-class.json \
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json)
test "$before" = "$after"
printf '%s\n' S16_T01_CENSUS_OK
