#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

s06=prd/migration/rust-evidence/m204-s06-requirement-evidence.json
s07=prd/migration/rust-evidence/m204-s07-requirement-evidence.json
s10=prd/migration/rust-evidence/m204-s10-requirement-evidence.json
s14=prd/migration/rust-evidence/m204-s14-c4-acceptance.json
s14_manifest=prd/migration/rust-evidence/m204-s14-frozen-hashes.json
artifact=prd/migration/rust-evidence/m204-s15-requirement-class.json
before_file=scripts/.m204_s15_t02_before.sha256
after_file=scripts/.m204_s15_t02_after.sha256
trap 'rm -f "$before_file" "$after_file"' EXIT

sha256sum "$s06" "$s07" "$s10" "$s14" "$s14_manifest" >"$before_file"
bash -n scripts/m204_s15_t02_verify.sh
uv run ruff format --check scripts/m204_s15_requirement_class.py scripts/test_m204_s15_requirement_class.py
bash -n scripts/m204_s15_t01_verify.sh
uv run python scripts/test_m204_s15_requirement_class.py
uv run python scripts/m204_s15_requirement_class.py check --out "$artifact"
classification=$(uv run python scripts/m204_s15_requirement_class.py classify)
expected='{"c4_acceptance":"non-pass","classification":"supporting-only","class_matched_ids":[],"status_effect":"unchanged"}'
if [[ "$classification" != "$expected" ]]; then
  printf 'unexpected classify output: %s\n' "$classification" >&2
  exit 1
fi
uv run python - "$artifact" <<'PY'
import json
import sys
from pathlib import Path

artifact = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert artifact["class_matched_ids"] == []
assert artifact["status_effect"] == "unchanged"
assert all(row["class_matched"] is False for row in artifact["rows"])
assert all(row["status_effect"] == "unchanged" for row in artifact["rows"])
assert [row["requirement_id"] for row in artifact["rows"]] == [
    "R038", "R063", "R064", "R081", "R035", "R070", "R066", "R073", "R000", "R999"
]
assert artifact["rows"][-2]["evidence_class"] == "reserved-stub"
assert artifact["rows"][-1]["evidence_class"] == "reserved-stub"
print("S15_T02_ARTIFACT_ASSERTIONS_OK")
PY
sha256sum "$s06" "$s07" "$s10" "$s14" "$s14_manifest" >"$after_file"
if ! cmp -s "$before_file" "$after_file"; then
  printf 'historical or S14 inputs changed during T02 verification\n' >&2
  exit 1
fi
printf 'S15_T02_NEGATIVES_OK tests=26\n'
