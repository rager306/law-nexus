#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="prd/migration/rust-evidence/m204-s11-c4-failed-classification.json"
MANIFEST="prd/migration/rust-evidence/m204-s11-frozen-hashes.json"
TMP_DIR="$(mktemp -d)"
TMP_OUT="$TMP_DIR/classification.json"
trap 'rm -rf "$TMP_DIR"' EXIT

# Composer is intentionally subprocess-only and never receives a corpus root.
uv run python scripts/m204_s11_classify.py --out "$TMP_OUT"
uv run python scripts/test_m204_s11_classify.py

# Publish immutable evidence only after the bounded tests pass.
if [[ -e "$OUT" ]]; then
  cmp -s "$TMP_OUT" "$OUT" || { echo "classification output already exists and differs" >&2; exit 1; }
else
  cp "$TMP_OUT" "$OUT"
fi

uv run python - "$MANIFEST" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
root = Path.cwd()
paths = [
    "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json",
    "prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl",
    "prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json",
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json",
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/full-walk-001/diagnostics.jsonl",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/eligible-run-001/diagnostics.jsonl",
    "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json",
    "prd/migration/rust-evidence/m204-s07-verification-battery.json",
]
rows = []
for relative in paths:
    path = root / relative
    if not path.is_file():
        raise SystemExit(f"missing frozen input: {relative}")
    rows.append({
        "path": relative,
        "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    })
value = {
    "schema": "law-nexus/m204-s11-frozen-hashes/v1",
    "scope": "S11 T01 classification inputs; tracked evidence only",
    "files": rows,
    "non_claims": [
        "hash pins do not identify the failed file",
        "hash pins do not make C4 operational acceptance pass",
        "hash pins do not settle a milestone.validate attempt",
    ],
}
encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
if manifest.exists():
    if manifest.read_text(encoding="utf-8") != encoded:
        raise SystemExit(f"immutable manifest already exists and differs: {manifest}")
else:
    manifest.write_text(encoded, encoding="utf-8")
PY

uv run ruff check scripts/m204_s11_classify.py scripts/test_m204_s11_classify.py
uv run ruff format --check scripts/m204_s11_classify.py scripts/test_m204_s11_classify.py

uv run python - "$OUT" "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

classification = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert classification["marker"] == "S11_T01_CLASSIFICATION_OK"
assert classification["jsonl"]["parseable"] is True
assert classification["jsonl"]["duplicate_digests_equal"] is True
assert classification["historical_predicates"]["s07_first_digest_valid"] is True
assert classification["historical_predicates"]["s10_duplicate_digest_valid"] is False
assert classification["product_failed"] == {
    "files": 43797,
    "decoded": 43796,
    "failed": 1,
    "stable_across": ["S07 full-walk", "S07 eligible", "S10 full-walk"],
    "identity_of_failed_file": "unresolved",
    "failure_class": "unresolved without per-file provenance; aggregate only",
}
assert classification["battery_failed_check"]["check_id"] == "operational-c4-acceptance"
assert classification["battery_failed_check"]["distinct_from_product_failed"] is True
assert classification["s10_historical_facts_preserved"]["receipt_jsonl_valid"] is False
assert len(manifest["files"]) == 9
assert all(row["sha256"].startswith("sha256:") for row in manifest["files"])
print("S11_T01_CLASSIFICATION_OK")
PY
