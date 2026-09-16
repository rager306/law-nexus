#!/usr/bin/env bash
# Offline closeout chain for the M207 S03 frozen evaluation (T06).
#
# MACHINE HALF (always provable, never claims a human):
#
#   * the nine frozen battery rows in their own `check` mode, each named exactly
#     as the verifier's frozen closed set demands (`s03_schemas`,
#     `s03_eval_manifest`, `s03_metrics`, `s03_hostile_suite`,
#     `s03_machinery_verifier`, `s02_regression`, `ruff_format`, `ruff_check`,
#     `adr_conformance`).  Any other id in the result table is refused by
#     battery mode with SCHEMA_KEY_DRIFT, so the frozen battery schema stays
#     intact;
#   * the marker each gate carries is required, not merely its exit code: a gate
#     that exits 0 without printing its own marker is SUBCLI_FAILURE.  The
#     machinery verifier may print M207_S03_MACHINERY_OK (human absent) or
#     M207_S03_MACHINERY_HUMAN_DATA_PRESENT (human reference present) -- never
#     the human-gate marker, which only this chain owns;
#   * the S02 closeout chain as a real subprocess; exit 0 (a human pilot
#     happened) and exit 3 (honest HUMAN_PILOT_ABSENT) are both green, anything
#     else is S02_REGRESSION_FAILED.  The row records exit_code 0 because the
#     *boundary* is green; the accepted child exits are named in the row's
#     command column (`exit 0 or 3 accepted`), so a reader of the tracked
#     battery never mistakes a normalized 3 for a raw 0;
#   * the four chain-level pins the slice plan flagged, deliberately NOT battery
#     rows (the battery's check set is the frozen closed set of nine): exactly
#     180 `.txt` fragments, `npa_lawref_sample_contract`, `r035_proof_gate`,
#     `r070_proof_gate`.  R035 and R070 stay HOLD -- a green pin is not a status
#     change -- and R074 is untouched because no `crates/**` file changes (D487);
#   * `ruff format --check`, `ruff check` over the S03 Python surface and
#     `scripts/verify-adr-conformance.py` (finding_count=0).
#
# HUMAN HALF (never fabricated):
#
#   * `run` modes over the FIXED human stores (D480) -- the intake gate over
#     prd/annotation/m207-s02-submissions, then agreement, then the adjudication
#     gate over prd/annotation/m207-s02-adjudications -- and then the S03 metrics
#     engine, which publishes prd/migration/rust-evidence/m207-s03-evaluation-
#     report.json.  The chain never creates, edits or deletes a submission or an
#     adjudication file, and passes no test-fixture escape hatch
#     (`--allow-test-fixtures` is refused by `metrics check` anyway);
#   * with no human coding the chain exits 3 with HUMAN_PILOT_ABSENT /
#     MACHINERY_GREEN_HUMAN_ABSENT, prints M207_S03_MACHINERY_OK as its last line
#     and creates no evaluation report: "zero codings" is never reported as
#     success, no rate is published and the slice stays blocked;
#   * the `absent_only` predicate is copied verbatim from the S02 chain: an exit
#     outside {0,3} from a run stage is a DEFECT (exit 1), never a blocker.  A
#     refused proxy producer exits 1 and must not be laundered into the
#     "no human, machinery green" path (RC28-F01, scenario 5);
#   * M207_S03_VERIFY_OK is printed, with exit 0, only when the human stages
#     validated, the tracked battery records human_pilot_performed=true and the
#     verifier re-run reports M207_S03_MACHINERY_HUMAN_DATA_PRESENT.
#
# FAIL-CLOSED GUARDS:
#
#   * a `run` stage that exits non-zero must not have created or modified its own
#     derived artifact -- a partial human artifact without a validated stage is a
#     hard failure, not a blocker;
#   * the chain takes NO arguments: it never accepts `--root`, because a foreign
#     forged tree with a self-consistent store would otherwise reach VERIFY_OK
#     (scenario 7).  The root is derived from BASH_SOURCE;
#   * the battery opt-in is read once and then *unset together with the S02
#     opt-in*: no child process (the hostile suite, the verifier, a gate) may
#     inherit a mode-switching variable, and the mandatory post-write read-only
#     pass below can never silently rewrite the tracked artifact -- which would
#     make BATTERY_STALE unobservable (write mode never fails).  Only the single
#     battery command below receives `--write`;
#   * the chain is READ-ONLY with respect to the tracked battery unless
#     M207_S03_WRITE_BATTERY=1 is set, which regenerates
#     prd/migration/rust-evidence/m207-s03-battery.json exactly once, before host
#     verification (D473), and is then confirmed by a read-only run that must
#     stay current.  Any other invocation compares the freshly assembled payload
#     byte-for-byte with the tracked file and fails closed with BATTERY_STALE.
#
# Operator workflow for the human pilot:
#   1. hand the two kits (prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json
#      and ...-pass2.json) to two independent coders;
#   2. drop the two envelopes into prd/annotation/m207-s02-submissions and the
#      adjudications into prd/annotation/m207-s02-adjudications, re-run this chain;
#   3. re-run once with M207_S03_WRITE_BATTERY=1 so the tracked battery records
#      human_pilot_performed=true, then re-run without it: it must stay green and
#      end with M207_S03_VERIFY_OK as its last line.
set -euo pipefail

readonly MARKER="M207_S03_VERIFY_OK"
readonly MACHINERY_MARKER="M207_S03_MACHINERY_OK"
readonly HUMAN_DATA_MARKER="M207_S03_MACHINERY_HUMAN_DATA_PRESENT"
readonly ABSENT_TOKEN="MACHINERY_GREEN_HUMAN_ABSENT"
readonly ABSENT_DIAGNOSTIC="HUMAN_PILOT_ABSENT"
readonly ABSENT_EXIT=3
readonly FAIL_EXIT=1

# The closing chain never accepts a foreign root: a forged tree would otherwise
# be indistinguishable from the repository (scenario 7).  Named, fail-closed.
if [ "$#" -ne 0 ]; then
  printf 'FAIL UNSAFE_PATH: the closing chain takes no arguments; --root is refused and the repository root comes from BASH_SOURCE\n' >&2
  exit "$FAIL_EXIT"
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

readonly EVIDENCE="prd/migration/rust-evidence"
readonly BATTERY="$EVIDENCE/m207-s03-battery.json"
readonly REPORT="$EVIDENCE/m207-s03-evaluation-report.json"
readonly SUBMISSION_STORE="prd/annotation/m207-s02-submissions"
readonly ADJUDICATION_STORE="prd/annotation/m207-s02-adjudications"
readonly INTAKE_RECORD="$EVIDENCE/m207-s02-intake-record.json"
readonly AGREEMENT_REPORT="$EVIDENCE/m207-s02-agreement-report.json"
readonly INVENTORY="$EVIDENCE/m207-s02-disagreement-inventory.json"
readonly ADJUDICATION_RECORD="$EVIDENCE/m207-s02-adjudication-record.json"
readonly RECEIPT="$EVIDENCE/m207-s02-pilot-receipt.json"

readonly FRAGMENT_COUNT_CHECK='test "$(find crates/ln-decode/tests/fixtures/npa-lawref -name "*.txt" | wc -l | tr -d " ")" = 180'
readonly CARGO_NPA_CONTRACT="cargo test -p ln-decode --offline --test npa_lawref_sample_contract"
readonly CARGO_R035="cargo test -p ln-kb-ontology --offline --test r035_proof_gate"
readonly CARGO_R070="cargo test -p ln-temporal --offline --test r070_proof_gate"

# The Python surface the formatter and the linter cover (the bash chain is not
# Python; the S02 scripts are covered by the S02 chain's own ruff rows).
readonly CHECKS=(
  scripts/m207_s03_schemas.py
  scripts/m207_s03_eval_manifest.py
  scripts/m207_s03_metrics.py
  scripts/m207_s03_pilot.py
  scripts/test_m207_s03_pilot.py
)

results="$(mktemp -t m207-s03-results-XXXXXX)"
stage_log="$(mktemp -t m207-s03-stage-XXXXXX)"
trap 'rm -f "$results" "$stage_log"' EXIT

# Read the D473 opt-in once and keep the ambient environment clean for every
# child process; both write flags are cleared so a read-only pass stays read-only.
# Only the battery command below is handed `--write`.
write_battery=0
if [ "${M207_S03_WRITE_BATTERY:-0}" = "1" ]; then
  write_battery=1
fi
unset M207_S03_WRITE_BATTERY
unset M207_S02_WRITE_BATTERY

failed=0

# Battery rows: `id<TAB>status<TAB>durationMs<TAB>command`, in a fixed order.
# The command column must be byte-stable across runs: the tracked battery is
# compared byte-for-byte, so no absolute or temporary path may reach it.
run() {
  local id="$1"
  shift
  local command="$*"
  local start end status
  start="$(date +%s%N)"
  : >"$stage_log"
  if "$@" >"$stage_log" 2>&1; then
    status=0
  else
    status=$?
    failed=1
  fi
  end="$(date +%s%N)"
  printf '%s\t%d\t%d\t%s\n' "$id" "$status" "$(((end - start) / 1000000))" "$command" >>"$results"
  printf '[m207-s03] %-22s exit=%d %7dms %s\n' \
    "$id" "$status" "$(((end - start) / 1000000))" "$command"
  if [ "$status" -eq 0 ]; then
    tail -n 2 "$stage_log" | sed 's/^/    /'
  else
    tail -n 25 "$stage_log" | sed 's/^/    /'
  fi
}

# A battery row whose gate must also print the marker it claims: a zero exit
# without the marker is a contract failure, not a success.
run_marker() {
  local id="$1"
  local pattern="$2"
  shift 2
  local command="$*"
  local start end status
  start="$(date +%s%N)"
  : >"$stage_log"
  if "$@" >"$stage_log" 2>&1; then
    status=0
  else
    status=$?
    failed=1
  fi
  if [ "$status" -eq 0 ] && ! grep -Eq "$pattern" "$stage_log"; then
    printf 'FAIL SUBCLI_FAILURE: %s exited 0 without printing %s\n' "$id" "$pattern" >&2
    status=1
    failed=1
  fi
  end="$(date +%s%N)"
  printf '%s\t%d\t%d\t%s\n' "$id" "$status" "$(((end - start) / 1000000))" "$command" >>"$results"
  printf '[m207-s03] %-22s exit=%d %7dms %s\n' \
    "$id" "$status" "$(((end - start) / 1000000))" "$command"
  tail -n 2 "$stage_log" | sed 's/^/    /'
}

# The S02 boundary is green on exit 0 (human pilot performed) and on exit 3
# (honest absence); the row records the boundary verdict, and its command column
# names the accepted child exits.  Anything else is S02_REGRESSION_FAILED.
run_regression() {
  local id="$1"
  shift
  local command="$* (exit 0 or 3 accepted)"
  local start end status
  start="$(date +%s%N)"
  : >"$stage_log"
  if "$@" >"$stage_log" 2>&1; then
    status=0
  else
    status=$?
  fi
  end="$(date +%s%N)"
  if [ "$status" -eq 0 ] || [ "$status" -eq "$ABSENT_EXIT" ]; then
    printf '[m207-s03] %-22s exit=%d accepted (0 or 3 = green boundary) %7dms\n' \
      "$id" "$status" "$(((end - start) / 1000000))"
    printf '%s\t0\t%d\t%s\n' "$id" "$(((end - start) / 1000000))" "$command" >>"$results"
  else
    printf 'FAIL S02_REGRESSION_FAILED: %s exited %d; only 0 (human pilot performed) and 3 (HUMAN_PILOT_ABSENT) are green\n' \
      "$id" "$status" >&2
    printf '%s\t%d\t%d\t%s\n' "$id" "$status" "$(((end - start) / 1000000))" "$command" >>"$results"
    failed=1
  fi
  tail -n 5 "$stage_log" | sed 's/^/    /'
}

# Chain-level gates outside the frozen battery check set.
run_extra() {
  local id="$1"
  local command="$2"
  shift 2
  local start end status
  start="$(date +%s%N)"
  : >"$stage_log"
  if "$@" >"$stage_log" 2>&1; then
    status=0
  else
    status=$?
    failed=1
  fi
  end="$(date +%s%N)"
  printf '[m207-s03] %-22s exit=%d %7dms %s\n' \
    "$id" "$status" "$(((end - start) / 1000000))" "$command"
  if [ "$status" -eq 0 ]; then
    tail -n 2 "$stage_log" | sed 's/^/    /'
  else
    tail -n 25 "$stage_log" | sed 's/^/    /'
  fi
}

# The human `run` stages: capture the tool's own verdict verbatim.
run_human_stage() {
  local id="$1"
  shift
  local status=0
  : >"$stage_log"
  if uv run python "$@" >"$stage_log" 2>&1; then
    status=0
  else
    status=$?
  fi
  printf '[m207-s03] %-22s exit=%d\n' "$id" "$status"
  sed 's/^/    /' "$stage_log"
  return "$status"
}

digest_or_missing() {
  if [ -f "$1" ]; then
    sha256sum "$1" | cut -d' ' -f1
  else
    printf '%s' "MISSING"
  fi
}

battery_human_flag() {
  uv run python -c 'import json, sys; doc = json.load(open(sys.argv[1], encoding="utf-8")); print(str(doc.get("human_pilot_performed")).lower())' "$1"
}

printf '%s\n' '[m207-s03] offline S03 closeout chain'

# --------------------------------------------------------------------------- #
# 1. Human half: the real store `run` modes plus the metrics engine.  Nothing
#    here fabricates a coding, and nothing here is written without a validated
#    stage.  This runs first because the report published here is an input of
#    the metrics and machinery checks below: with a human reference present the
#    verifier refuses a missing report (REPORT_MISSING_WITH_HUMAN_DATA).
# --------------------------------------------------------------------------- #
printf '%s\n' '[m207-s03] human pilot phase (run modes over the fixed human stores)'
before_intake="$(digest_or_missing "$INTAKE_RECORD")"
before_report="$(digest_or_missing "$AGREEMENT_REPORT")"
before_inventory="$(digest_or_missing "$INVENTORY")"
before_adjudication="$(digest_or_missing "$ADJUDICATION_RECORD")"
before_receipt="$(digest_or_missing "$RECEIPT")"
before_evaluation="$(digest_or_missing "$REPORT")"

intake_status=0
agreement_status=0
adjudication_status=0
metrics_status=0

run_human_stage intake-run scripts/m207_s02_intake.py run \
  --store "$SUBMISSION_STORE" --record "$INTAKE_RECORD" || intake_status=$?
if [ "$intake_status" -eq 0 ]; then
  run_human_stage agreement-run scripts/m207_s02_agreement.py run \
    --store "$SUBMISSION_STORE" --intake "$INTAKE_RECORD" \
    --report "$AGREEMENT_REPORT" --inventory "$INVENTORY" || agreement_status=$?
fi
if [ "$intake_status" -eq 0 ] && [ "$agreement_status" -eq 0 ]; then
  run_human_stage adjudication-run scripts/m207_s02_adjudicate.py run \
    --store "$ADJUDICATION_STORE" --agreement "$AGREEMENT_REPORT" \
    --inventory "$INVENTORY" --record "$ADJUDICATION_RECORD" \
    --receipt "$RECEIPT" || adjudication_status=$?
fi
if [ "$intake_status" -eq 0 ] && [ "$agreement_status" -eq 0 ] && [ "$adjudication_status" -eq 0 ]; then
  run_human_stage metrics-run scripts/m207_s03_metrics.py run \
    --submissions "$SUBMISSION_STORE" --adjudications "$ADJUDICATION_STORE" \
    --intake-record "$INTAKE_RECORD" --agreement-report "$AGREEMENT_REPORT" \
    --inventory "$INVENTORY" --adjudication-record "$ADJUDICATION_RECORD" \
    --pilot-receipt "$RECEIPT" --report "$REPORT" || metrics_status=$?
fi

# Fail closed: a stage that refused must not have left its own evidence behind.
if [ "$intake_status" -ne 0 ] && [ "$(digest_or_missing "$INTAKE_RECORD")" != "$before_intake" ]; then
  printf 'FAIL %s: the intake run exited %d yet wrote %s\n' \
    "$ABSENT_DIAGNOSTIC" "$intake_status" "$INTAKE_RECORD" >&2
  exit "$FAIL_EXIT"
fi
if [ "$agreement_status" -ne 0 ] &&
  { [ "$(digest_or_missing "$AGREEMENT_REPORT")" != "$before_report" ] ||
    [ "$(digest_or_missing "$INVENTORY")" != "$before_inventory" ]; }; then
  printf 'FAIL %s: the agreement run exited %d yet wrote its report or inventory\n' \
    "$ABSENT_DIAGNOSTIC" "$agreement_status" >&2
  exit "$FAIL_EXIT"
fi
if [ "$adjudication_status" -ne 0 ] &&
  { [ "$(digest_or_missing "$ADJUDICATION_RECORD")" != "$before_adjudication" ] ||
    [ "$(digest_or_missing "$RECEIPT")" != "$before_receipt" ]; }; then
  printf 'FAIL %s: the adjudication run exited %d yet wrote its record or receipt\n' \
    "$ABSENT_DIAGNOSTIC" "$adjudication_status" >&2
  exit "$FAIL_EXIT"
fi
if [ "$metrics_status" -ne 0 ] && [ "$(digest_or_missing "$REPORT")" != "$before_evaluation" ]; then
  printf 'FAIL %s: the metrics run exited %d yet wrote %s\n' \
    "$ABSENT_DIAGNOSTIC" "$metrics_status" "$REPORT" >&2
  exit "$FAIL_EXIT"
fi

human_present=0
if [ "$intake_status" -eq 0 ] && [ "$agreement_status" -eq 0 ] &&
  [ "$adjudication_status" -eq 0 ] && [ "$metrics_status" -eq 0 ]; then
  if [ ! -f "$REPORT" ]; then
    printf 'FAIL %s: the metrics run exited 0 yet %s does not exist\n' \
      "$ABSENT_DIAGNOSTIC" "$REPORT" >&2
    exit "$FAIL_EXIT"
  fi
  human_present=1
  printf '%s\n' '[m207-s03] the human contour reported success on all four stages'
elif [ "$intake_status" -eq 0 ] && [ "$agreement_status" -eq 0 ] && [ "$adjudication_status" -eq 0 ]; then
  printf 'FAIL %s: the human stages validated but the metrics engine exited %d; this is a defect, not a missing human\n' \
    "$ABSENT_DIAGNOSTIC" "$metrics_status" >&2
  exit "$FAIL_EXIT"
else
  # The S02 `absent_only` predicate: only 0 and 3 are lawful for a run stage.
  absent_only=1
  for status in "$intake_status" "$agreement_status" "$adjudication_status"; do
    if [ "$status" -ne 0 ] && [ "$status" -ne "$ABSENT_EXIT" ]; then
      absent_only=0
    fi
  done
  if [ "$absent_only" -ne 1 ]; then
    printf 'FAIL %s: a run stage failed with a status other than absence (intake=%d agreement=%d adjudication=%d); this is a defect, not a missing human\n' \
      "$ABSENT_DIAGNOSTIC" "$intake_status" "$agreement_status" "$adjudication_status" >&2
    exit "$FAIL_EXIT"
  fi
fi

# --------------------------------------------------------------------------- #
# 2. Machinery: the nine frozen battery rows.  Every id below is one of the
#    nine ids the verifier declares; battery mode refuses any other set.
# --------------------------------------------------------------------------- #
run_marker s03_schemas 'M207_S03_SCHEMAS_OK' \
  uv run python scripts/m207_s03_schemas.py check
run_marker s03_eval_manifest 'M207_S03_EVAL_MANIFEST_OK' \
  uv run python scripts/m207_s03_eval_manifest.py check
run_marker s03_metrics 'M207_S03_METRICS_OK' \
  uv run python scripts/m207_s03_metrics.py check
run_marker s03_hostile_suite '^OK' \
  uv run python scripts/test_m207_s03_pilot.py
run_marker s03_machinery_verifier 'M207_S03_MACHINERY_OK|M207_S03_MACHINERY_HUMAN_DATA_PRESENT' \
  uv run python scripts/m207_s03_pilot.py check
run_regression s02_regression bash scripts/m207_s02_t07_verify.sh
run ruff_format uv run ruff format --check "${CHECKS[@]}"
run ruff_check uv run ruff check "${CHECKS[@]}"
run_marker adr_conformance '"finding_count": ?0' \
  uv run python scripts/verify-adr-conformance.py

# --------------------------------------------------------------------------- #
# 3. Chain-level pins the slice plan flagged (not battery rows).
# --------------------------------------------------------------------------- #
run_extra fragment-count "$FRAGMENT_COUNT_CHECK" bash -c "$FRAGMENT_COUNT_CHECK"
run_extra cargo-npa-lawref-contract "$CARGO_NPA_CONTRACT" \
  cargo test -p ln-decode --offline --test npa_lawref_sample_contract
run_extra cargo-r035-proof-gate "$CARGO_R035" \
  cargo test -p ln-kb-ontology --offline --test r035_proof_gate
run_extra cargo-r070-proof-gate "$CARGO_R070" \
  cargo test -p ln-temporal --offline --test r070_proof_gate

if [ "$failed" -ne 0 ]; then
  printf '%s\n' '[m207-s03] FAILED -- the machinery contour is red; see the failing check above' >&2
  exit "$FAIL_EXIT"
fi

# --------------------------------------------------------------------------- #
# 4. Battery: assemble from the result table (write only under the D473 opt-in),
#    then confirm with a read-only pass that must stay current.  The opt-in was
#    unset at the top, so the confirmation run cannot silently rewrite anything.
# --------------------------------------------------------------------------- #
if [ "$write_battery" -eq 1 ]; then
  printf '%s\n' '[m207-s03] M207_S03_WRITE_BATTERY=1: regenerating the tracked battery once'
  # The opt-in was read once at the top and then unset, so the authorization is
  # re-supplied to this one command only: `--write` without M207_S03_WRITE_BATTERY=1
  # is refused by the tool itself (AUTHORITY_CLAIM), and the read-only
  # confirmation below still runs with a clean environment.
  if ! M207_S03_WRITE_BATTERY=1 uv run python scripts/m207_s03_pilot.py battery \
    --results "$results" --out "$BATTERY" --write; then
    printf '%s\n' '[m207-s03] FAILED -- the authorized battery write failed' >&2
    exit "$FAIL_EXIT"
  fi
fi
battery_status=0
uv run python scripts/m207_s03_pilot.py battery --results "$results" --out "$BATTERY" ||
  battery_status=$?
if [ "$battery_status" -ne 0 ]; then
  printf '%s\n' '[m207-s03] FAILED -- the tracked battery is stale or malformed; regenerate once with M207_S03_WRITE_BATTERY=1 before host verification' >&2
  exit "$FAIL_EXIT"
fi

# --------------------------------------------------------------------------- #
# 5. The human gate marker.  Exit 0 only on real, separately adjudicated codings.
# --------------------------------------------------------------------------- #
if [ "$human_present" -eq 0 ]; then
  printf '%s\n' \
    "FAIL $ABSENT_DIAGNOSTIC: no human pilot exists -- two independent human codings in $SUBMISSION_STORE and a separate human adjudication in $ADJUDICATION_STORE are required; without both stores no denominator exists, so no rate may be published and the harness fabricates neither" >&2
  printf '%s machinery_green=1 human_pilot_performed=false\n' "$ABSENT_TOKEN"
  printf '%s human=%s\n' "$MACHINERY_MARKER" "$ABSENT_TOKEN"
  exit "$ABSENT_EXIT"
fi

if [ "$(battery_human_flag "$BATTERY")" != "true" ]; then
  printf 'FAIL %s: a human pilot exists but the tracked battery still records human_pilot_performed=false; regenerate it once with M207_S03_WRITE_BATTERY=1\n' \
    "$ABSENT_DIAGNOSTIC" >&2
  exit "$FAIL_EXIT"
fi

human_verify_status=0
if uv run python scripts/m207_s03_pilot.py check >"$stage_log" 2>&1; then
  human_verify_status=0
else
  human_verify_status=$?
fi
sed 's/^/    /' "$stage_log"
if [ "$human_verify_status" -ne 0 ]; then
  printf '%s\n' '[m207-s03] FAILED -- the verifier rejected the human pilot contour' >&2
  exit "$FAIL_EXIT"
fi
if ! grep -q "$HUMAN_DATA_MARKER" "$stage_log"; then
  printf 'FAIL %s: the verifier did not report human data present after a green human pilot\n' \
    "$ABSENT_DIAGNOSTIC" >&2
  exit "$FAIL_EXIT"
fi

printf '%s\n' "$MARKER"
