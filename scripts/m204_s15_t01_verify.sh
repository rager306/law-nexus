#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s15-requirement-class.json
manifest=prd/migration/rust-evidence/m204-s15-frozen-hashes.json
before=$(sha256sum \
  prd/migration/rust-evidence/m204-s06-requirement-evidence.json \
  prd/migration/rust-evidence/m204-s07-requirement-evidence.json \
  prd/migration/rust-evidence/m204-s10-requirement-evidence.json \
  prd/migration/rust-evidence/m204-s14-c4-acceptance.json \
  prd/migration/rust-evidence/m204-s14-frozen-hashes.json)
uv run python scripts/m204_s15_requirement_class.py compose
uv run python scripts/m204_s15_requirement_class.py check
classification=$(uv run python scripts/m204_s15_requirement_class.py classify)
test "$classification" = '{"c4_acceptance":"non-pass","classification":"supporting-only","class_matched_ids":[],"status_effect":"unchanged"}'
uv run python scripts/test_m204_s15_requirement_class.py
uv run python - "$artifact" "$manifest" <<'PY'
import json
import sys
from pathlib import Path
artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert artifact["schema"] == "law-nexus/m204-s15-requirement-class/v1"
assert artifact["c4_acceptance"] == "non-pass"
assert artifact["classification"] == "supporting-only"
assert artifact["status_effect"] == "unchanged"
assert artifact["class_matched_ids"] == []
assert artifact["s15_called_validate_milestone"] is False
assert artifact["s15_called_requirement_update"] is False
assert artifact["open_findings"] == 19
assert [row["requirement_id"] for row in artifact["rows"]] == ["R038", "R063", "R064", "R081", "R035", "R070", "R066", "R073", "R000", "R999"]
assert len(manifest["files"]) == 5
print("S15_T01_CLASS_OK")
PY
after=$(sha256sum \
  prd/migration/rust-evidence/m204-s06-requirement-evidence.json \
  prd/migration/rust-evidence/m204-s07-requirement-evidence.json \
  prd/migration/rust-evidence/m204-s10-requirement-evidence.json \
  prd/migration/rust-evidence/m204-s14-c4-acceptance.json \
  prd/migration/rust-evidence/m204-s14-frozen-hashes.json)
test "$before" = "$after"
printf '%s\n' S15_T01_VERIFY_OK
