#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
receipt="prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json"
uv run python scripts/m204_s10_c4_run.py --verify-receipt "$receipt"
uv run python - "$receipt" <<'PY'
import json
import sys
from pathlib import Path

receipt = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert receipt["attempt_id"] == "s10-full-walk-001"
assert receipt["binary_profile"] == "debug"
assert receipt["c4_binding"]["jobs"] == 1
assert receipt["c4_binding"]["limit"] is None
assert receipt["corpus"]["consultant_xml_count"] == 43785
assert receipt["duration_ms"] >= 3_600_000
assert receipt["terminal"] == {
    "outcome": "complete",
    "exit_code": 0,
    "signal": None,
    "timeout": False,
}
assert receipt["observed_output"]["jsonl_valid"] is False
assert receipt["claims"]["operational_acceptance"] == "non-pass"
print("M204 S10 T03 BOUNDED INTEGRITY OK: genuine terminal receipt, operational non-pass")
PY
printf '%s\n' 'M204 S10 T03 VERIFY OK'
