#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
artifact=prd/migration/rust-evidence/m204-s14-c4-acceptance.json
before=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json \
  prd/migration/rust-evidence/m204-s11-c4-failed-classification.json \
  prd/migration/rust-evidence/m204-s13-s07-verification-battery.json)
uv run python scripts/m204_s14_polarity.py compose --out "$artifact"
uv run python scripts/m204_s14_polarity.py check --out "$artifact"
classification=$(uv run python scripts/m204_s14_polarity.py classify --out "$artifact")
test "$classification" = '{"integrity":"pass","c4_acceptance":"non-pass","classification":"supporting-only"}'
uv run python scripts/test_m204_s14_polarity.py
uv run python - "$artifact" <<'PY'
import json
import sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["c4_acceptance"] == "non-pass"
assert value["distinct_from_product_failed"] is True
assert value["integrity_pass_is_not_operational_pass"] is True
assert value["s10_bytes_rewritten"] is False
assert value["status_effect"] == "unchanged"
assert value["classification"] == "supporting-only"
assert value["s14_called_validate_milestone"] is False
assert set(value["surfaces"]) == {"s10_receipt", "s10_battery", "s11_classification", "s13_battery"}
print("S14_T01_POLARITY_OK")
PY
after=$(sha256sum \
  prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json \
  prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json \
  prd/migration/rust-evidence/m204-s11-c4-failed-classification.json \
  prd/migration/rust-evidence/m204-s13-s07-verification-battery.json)
test "$before" = "$after"
printf '%s\n' S14_T01_VERIFY_OK
