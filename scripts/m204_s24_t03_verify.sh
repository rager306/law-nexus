#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
cd "$root"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
find prd/migration/rust-evidence -maxdepth 1 -type f -name 'm204-s[0-2][0-3]-*' -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$tmp"

bash scripts/m204_s24_t01_verify.sh
uv run python scripts/m204_s24_battery.py check
uv run python scripts/test_m204_s24_liveness.py
uv run python scripts/m204_s23_c4_run.py --verify-receipt \
  prd/migration/rust-evidence/m204-s23-remediation-v2-c4-receipt.json \
  --require-operational-pass
uv run python scripts/m204_s22_liveness.py check
uv run ruff check scripts/m204_s24_battery.py scripts/test_m204_s24_liveness.py scripts/m204_s24_liveness.py
uv run ruff format --check scripts/m204_s24_battery.py scripts/test_m204_s24_liveness.py scripts/m204_s24_liveness.py
cargo test -p ln-consultant-parser --offline --locked -j 1 --test contour_diagnostics_contract

# T04 bounded scope proof: the live governor failure is external projection state,
# not an S24-owned evidence failure.  Do not rewrite .compat.json here.
governor_report="$(mktemp)"
trap 'rm -f "$tmp" "$governor_report"' EXIT
set +e
uv run python -m law_nexus_harness governor >"$governor_report" 2>&1
governor_status=$?
set -e
uv run python - "$governor_report" "$governor_status" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
status = int(sys.argv[2])
raw = report_path.read_text(encoding="utf-8")
report = json.loads(raw.splitlines()[0])
assert status != 0, "governor unexpectedly changed; rerun the full gate"
assert report.get("status") == "failure"
compat = [
    finding
    for finding in report.get("findings", [])
    if finding.get("rule_id") == "compat-marker-hygiene.contract"
    and finding.get("status") == "fail"
]
assert len(compat) == 1, "compat-marker failure provenance is not unique"
serialized = json.dumps(compat[0], sort_keys=True)
assert "first_offender=DECISIONS.md" in serialized
assert "m204-s24" not in raw
print("S24_T04_EXTERNAL_COMPAT_MARKER_SCOPE_OK")
PY

if ! cmp -s "$tmp" <(find prd/migration/rust-evidence -maxdepth 1 -type f -name 'm204-s[0-2][0-3]-*' -print0 | sort -z | xargs -0 sha256sum); then
  echo 'historical S07-S23 evidence changed during verification' >&2
  exit 1
fi

echo S24_T03_VERIFY_OK
