#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
OUT="prd/migration/rust-evidence/m203-s09-promotion-battery.json"
DEBT="prd/migration/rust-evidence/m203-s09-r035-r070-debt.json"
GATES="prd/architecture/npa-promotion-gates.json"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mapfile -t BINDING_INPUTS < <(uv run python - "$GATES" <<'PY'
import json, sys
from pathlib import Path
print("\n".join(json.loads(Path(sys.argv[1]).read_text())[
    "revision_binding"
]["binding_inputs"]))
PY
)
for input in "${BINDING_INPUTS[@]}"; do
  test -f "$input" || { echo "missing binding input: $input" >&2; exit 2; }
done
BINDING="sha256:$(printf '%s\n' "${BINDING_INPUTS[@]}" | xargs sha256sum | sort -k2 | awk '{print $1}' | sha256sum | awk '{print $1}')"

run_once() {
  local run_number="$1"
  local steps="$WORK/steps-${run_number}.jsonl"
  local report="$WORK/governor-${run_number}.json"
  : > "$steps"
  local run_status=pass
  run_step() {
    local leg="$1" command_text="$2" started finished duration rc
    started=$(date +%s%3N)
    set +e
    bash -c "$command_text" > /dev/null 2>&1
    rc=$?
    set -e
    finished=$(date +%s%3N); duration=$((finished - started))
    uv run python - "$steps" "$leg" "$command_text" "$rc" "$duration" "$BINDING" <<'PY'
import json, sys
from pathlib import Path
record = {"leg": sys.argv[2], "command": sys.argv[3], "exit_code": int(sys.argv[4]),
          "duration_ms": int(sys.argv[5]), "revision_binding": sys.argv[6]}
with Path(sys.argv[1]).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
PY
    (( rc == 0 )) || run_status=fail
  }

  run_step contract 'cargo test -p ln-consultant-parser --offline --test promotion_gate_contract --test gold_ladder_contract --test gold_coding_contract --test drift_baseline_contract'

  # Capture and validate the structured governor report in the same leg.
  local started finished duration rc
  started=$(date +%s%3N)
  set +e
  uv run python -m law_nexus_harness governor > "$report" 2>/dev/null
  rc=$?
  set -e
  finished=$(date +%s%3N); duration=$((finished - started))
  # Keep report parsing as an explicit, observable battery step rather than
  # folding its result into the governor process exit code.
  local report_rc=0
  uv run python scripts/npa_s09_battery_report.py "$report" > /dev/null 2>&1 || report_rc=$?
  uv run python - "$steps" "$rc" "$duration" "$BINDING" <<'PY'
import json, sys
from pathlib import Path
record = {"leg": "integration", "command": "uv run python -m law_nexus_harness governor",
          "exit_code": int(sys.argv[2]), "duration_ms": int(sys.argv[3]),
          "revision_binding": sys.argv[4]}
with Path(sys.argv[1]).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
PY
  (( rc == 0 )) || run_status=fail
  uv run python - "$steps" "$report_rc" "$BINDING" <<'PY'
import json, sys
from pathlib import Path
record = {"leg": "integration", "command": "uv run python scripts/npa_s09_battery_report.py governor-report.json",
          "exit_code": int(sys.argv[2]), "duration_ms": 0,
          "revision_binding": sys.argv[3]}
with Path(sys.argv[1]).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
PY
  (( report_rc == 0 )) || run_status=fail

  run_step integration 'uv run python -m law_nexus_harness preflight'
  run_step integration 'uv run python scripts/verify-adr-conformance.py'
  run_step operational 'cargo run --offline --bin npa-gold-ladder -- --check'
  run_step operational 'cargo run --offline --bin npa-promotion-eval -- --check'
  run_step operational 'uv run python -c '\''import json; from pathlib import Path; p=json.loads(Path("prd/migration/rust-evidence/m203-s09-c4-operational-receipt.json").read_text()); assert {"schema","command","exit_code","revision_binding","binding_inputs","outcome"} <= p.keys(); assert p["schema"] == "npa-c4-operational-receipt/v1"; assert p["outcome"] == "fail-stale"'\'''

  uv run python - "$WORK/runs.jsonl" "$run_number" "$run_status" "$steps" <<'PY'
import json, sys
from pathlib import Path
steps = [json.loads(line) for line in Path(sys.argv[4]).read_text().splitlines() if line]
record = {"run": int(sys.argv[2]), "status": sys.argv[3], "steps": steps}
with Path(sys.argv[1]).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
PY
}

: > "$WORK/runs.jsonl"
run_once 1
run_once 2

# This projection is generated from the gates contract, never hand-maintained.
# Write it only after all host checks have finished: the output is tracked and
# changing it during a verification run invalidates source-integrity evidence.
uv run python - "$GATES" "$DEBT" <<'PY'
import json, sys
from pathlib import Path
gates = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
debt = gates["requirement_transitions"]["debt"]
if [item["requirement"] for item in debt] != ["R035", "R070"]:
    raise SystemExit("unexpected requirement debt surface")
payload = json.dumps({
    "schema": "npa-promotion-debt/v1",
    "status": {item["requirement"]: "active" for item in debt},
    "transitions": "none",
    "debt": debt,
    "source": "prd/architecture/npa-promotion-gates.json#/requirement_transitions/debt",
}, ensure_ascii=True, separators=(",", ":")) + "\n"
output = Path(sys.argv[2])
if not output.exists() or output.read_text(encoding="utf-8") != payload:
    output.write_text(payload, encoding="utf-8")
PY

uv run python - "$OUT" "$BINDING" "$WORK/runs.jsonl" <<'PY'
import json, sys
from pathlib import Path
runs = [json.loads(line) for line in Path(sys.argv[3]).read_text().splitlines() if line]
payload = json.dumps({
    "schema": "npa-promotion-battery/v1",
    "revision_binding": sys.argv[2],
    "runs": runs,
    "repeatability": "same-current-revision-binding",
}, ensure_ascii=True, separators=(",", ":")) + "\n"
output = Path(sys.argv[1])
if len(runs) != 2 or any(run["status"] != "pass" for run in runs):
    output.write_text(payload, encoding="utf-8")
    raise SystemExit(1)
# Preserve an existing passing receipt so repeated verification is read-only.
# Per-step durations are diagnostic and naturally vary between runs; they must
# not cause a tracked receipt rewrite when its revision-bound result is already
# passing.
if output.exists():
    try:
        existing = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = None
    existing_is_current_pass = (
        isinstance(existing, dict)
        and existing.get("schema") == "npa-promotion-battery/v1"
        and existing.get("revision_binding") == sys.argv[2]
        and len(existing.get("runs", [])) == 2
        and all(
            run.get("status") == "pass"
            and len(run.get("steps", [])) == 8
            for run in existing["runs"]
        )
    )
else:
    existing_is_current_pass = False
if not existing_is_current_pass:
    output.write_text(payload, encoding="utf-8")
PY

echo "npa-s09 evidence battery: pass (2 runs, binding $BINDING)"
