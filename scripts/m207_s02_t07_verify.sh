#!/usr/bin/env bash
# Offline closeout chain for the M207 S02 two-coding human pilot (T07).
#
# MACHINE HALF (always provable, never claims a human):
#
#   * the five frozen slice gates in their own `check` mode, each with its own
#     marker (M207_S02_SCHEMAS_OK, M207_S02_CODER_KIT_OK, M207_S02_INTAKE_OK,
#     M207_S02_AGREEMENT_OK, M207_S02_ADJUDICATION_OK);
#   * the hostile subprocess suite (`scripts/test_m207_s02_pilot.py`);
#   * the independent slice verifier (`scripts/m207_s02_pilot.py check`), which
#     prints M207_S02_MACHINERY_OK and can never print the human-gate marker;
#   * the S01 closeout chain as a real subprocess (M207_S01_VERIFY_OK);
#   * the four re-tests the slice plan flagged as uncovered (180-fragment count
#     plus npa_lawref_sample_contract, r035_proof_gate, r070_proof_gate).  They
#     are deliberately NOT battery rows: the battery's check set is the frozen
#     closed set of eleven ids the verifier declares, and battery mode rejects any
#     unexpected check_id with SCHEMA_KEY_DRIFT.  They are chain-level gates, so
#     the frozen battery schema stays intact while the re-tests are covered.
#     The S01 closeout chain does not run cargo at all, so this is coverage, not
#     duplication;
#   * `ruff format --check` and `ruff check` over the S02 scripts, and
#     `scripts/verify-adr-conformance.py`.
#
# HUMAN HALF (never fabricated):
#
#   * `run` modes over the fixed human stores (D480) -- the intake gate over
#     prd/annotation/m207-s02-submissions, then agreement, then the adjudication
#     gate over prd/annotation/m207-s02-adjudications.  The harness never creates,
#     edits or deletes a submission or an adjudication file, and no test-fixture
#     escape hatch (`--allow-test-fixtures`) is passed here;
#   * with no human coding the chain exits 3 with HUMAN_PILOT_ABSENT /
#     MACHINERY_GREEN_HUMAN_ABSENT, prints M207_S02_MACHINERY_OK as its last line
#     and creates no submission, agreement or adjudication artifact: "zero
#     codings" is never reported as success and the slice stays blocked;
#   * M207_S02_VERIFY_OK is printed, with exit 0, only when both independent human
#     submissions validated (coder_pass 1 and 2, distinct coder_id,
#     provenance=human-reviewed), the agreement was computed and frozen before
#     adjudication, a separate adjudication with a human adjudicator was recorded,
#     the tracked battery records human_pilot_performed=true, and the verifier
#     re-run reports M207_S02_MACHINERY_HUMAN_DATA_PRESENT.
#
# FAIL-CLOSED GUARDS:
#
#   * a `run` stage that exits non-zero must not have created or modified its own
#     derived artifact -- a partial human artifact without a validated stage is a
#     hard failure, not a blocker;
#   * the chain never edits the human stores and never invents a coding;
#   * the battery opt-in is read once and then *unset*: no child process (the
#     hostile suite, the verifier, a gate) may inherit a mode-switching variable.
#     Only the single battery command below receives `--write`.
#
# The chain is READ-ONLY with respect to the tracked battery unless
# M207_S02_WRITE_BATTERY=1 is set, which regenerates
# prd/migration/rust-evidence/m207-s02-battery.json exactly once, before host
# verification (D473).  Any other invocation compares the freshly assembled
# payload byte-for-byte with the tracked file and fails closed with BATTERY_STALE.
#
# Operator workflow for the human pilot:
#   1. hand the two kits (prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json
#      and ...-pass2.json) to two independent coders;
#   2. drop the two envelopes into prd/annotation/m207-s02-submissions, re-run this
#      chain;
#   3. drop the adjudications into prd/annotation/m207-s02-adjudications, re-run;
#   4. re-run once with M207_S02_WRITE_BATTERY=1 so the tracked battery records
#      human_pilot_performed=true, then re-run without it: it must stay green and
#      end with M207_S02_VERIFY_OK.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

readonly MARKER="M207_S02_VERIFY_OK"
readonly MACHINERY_MARKER="M207_S02_MACHINERY_OK"
readonly HUMAN_DATA_MARKER="M207_S02_MACHINERY_HUMAN_DATA_PRESENT"
readonly ABSENT_TOKEN="MACHINERY_GREEN_HUMAN_ABSENT"
readonly ABSENT_DIAGNOSTIC="HUMAN_PILOT_ABSENT"
readonly ABSENT_EXIT=3
readonly FAIL_EXIT=1

readonly EVIDENCE="prd/migration/rust-evidence"
readonly BATTERY="$EVIDENCE/m207-s02-battery.json"
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

# The Python surface the formatter and the linter cover.
readonly CHECKS=(
  scripts/m207_s02_schemas.py
  scripts/m207_s02_coder_kit.py
  scripts/m207_s02_intake.py
  scripts/m207_s02_agreement.py
  scripts/m207_s02_adjudicate.py
  scripts/m207_s02_pilot.py
  scripts/test_m207_s02_pilot.py
)

results="$(mktemp -t m207-s02-results-XXXXXX)"
stage_log="$(mktemp -t m207-s02-stage-XXXXXX)"
trap 'rm -f "$results" "$stage_log"' EXIT

# Read the D473 opt-in once and keep the ambient environment clean for every
# child process; only the battery command is handed `--write`.
write_battery=0
if [ "${M207_S02_WRITE_BATTERY:-0}" = "1" ]; then
  write_battery=1
fi
unset M207_S02_WRITE_BATTERY

failed=0

# Battery rows: `id<TAB>status<TAB>durationMs<TAB>command`, in a fixed order.
run() {
  local id="$1"
  shift
  local command="$*"
  local start end status
  start="$(date +%s%N)"
  if "$@"; then
    status=0
  else
    status=$?
    failed=1
  fi
  end="$(date +%s%N)"
  printf '%s\t%d\t%d\t%s\n' "$id" "$status" "$(((end - start) / 1000000))" "$command" >>"$results"
  printf '[m207-s02] %-20s exit=%d\n' "$id" "$status"
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
  printf '[m207-s02] %-20s exit=%d %7dms %s\n' "$id" "$status" "$(((end - start) / 1000000))" "$command"
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
  printf '[m207-s02] %-20s exit=%d\n' "$id" "$status"
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

printf '%s\n' '[m207-s02] offline closeout chain'

# --------------------------------------------------------------------------- #
# 1. Machinery: the eleven battery checks.
# --------------------------------------------------------------------------- #
run gate-schemas uv run python scripts/m207_s02_schemas.py check
run gate-coder-kit uv run python scripts/m207_s02_coder_kit.py check
run gate-intake uv run python scripts/m207_s02_intake.py check
run gate-agreement uv run python scripts/m207_s02_agreement.py check
run gate-adjudication uv run python scripts/m207_s02_adjudicate.py check
run adversarial-suite uv run python scripts/test_m207_s02_pilot.py
run verifier-pilot uv run python scripts/m207_s02_pilot.py check
run s01-regression bash scripts/m207_s01_t04_verify.sh
run ruff-format-check uv run ruff format --check "${CHECKS[@]}"
run ruff-lint uv run ruff check "${CHECKS[@]}"
run adr-conformance uv run python scripts/verify-adr-conformance.py

# --------------------------------------------------------------------------- #
# 2. Chain-level re-tests the slice plan flagged as uncovered (not battery rows).
# --------------------------------------------------------------------------- #
run_extra cargo-fragment-count "$FRAGMENT_COUNT_CHECK" bash -c "$FRAGMENT_COUNT_CHECK"
run_extra cargo-npa-lawref-contract "$CARGO_NPA_CONTRACT" cargo test -p ln-decode --offline --test npa_lawref_sample_contract
run_extra cargo-r035-proof-gate "$CARGO_R035" cargo test -p ln-kb-ontology --offline --test r035_proof_gate
run_extra cargo-r070-proof-gate "$CARGO_R070" cargo test -p ln-temporal --offline --test r070_proof_gate

if [ "$failed" -ne 0 ]; then
  printf '%s\n' '[m207-s02] FAILED -- the machinery contour is red; see the failing check above' >&2
  exit "$FAIL_EXIT"
fi

# --------------------------------------------------------------------------- #
# 3. Human half: the real store `run` modes.  Nothing here fabricates a coding.
# --------------------------------------------------------------------------- #
printf '%s\n' '[m207-s02] human pilot phase (run modes over the human stores)'
before_intake="$(digest_or_missing "$INTAKE_RECORD")"
before_report="$(digest_or_missing "$AGREEMENT_REPORT")"
before_inventory="$(digest_or_missing "$INVENTORY")"
before_adjudication="$(digest_or_missing "$ADJUDICATION_RECORD")"
before_receipt="$(digest_or_missing "$RECEIPT")"

intake_status=0
agreement_status=0
adjudication_status=0

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

human_present=0
if [ "$intake_status" -eq 0 ] && [ "$agreement_status" -eq 0 ] && [ "$adjudication_status" -eq 0 ]; then
  human_present=1
  printf '%s\n' '[m207-s02] the human contour reported success on all three stages'
fi

# --------------------------------------------------------------------------- #
# 4. Battery: assemble from the result table (write only under the D473 opt-in).
# --------------------------------------------------------------------------- #
battery_args=(--results "$results" --out "$BATTERY")
if [ "$write_battery" -eq 1 ]; then
  battery_args+=(--write)
  printf '%s\n' '[m207-s02] M207_S02_WRITE_BATTERY=1: regenerating the tracked battery once'
fi
battery_status=0
uv run python scripts/m207_s02_pilot.py battery "${battery_args[@]}" || battery_status=$?
if [ "$battery_status" -ne 0 ]; then
  printf '%s\n' '[m207-s02] FAILED -- the tracked battery is stale or malformed; regenerate once with M207_S02_WRITE_BATTERY=1 before host verification' >&2
  exit "$FAIL_EXIT"
fi

# --------------------------------------------------------------------------- #
# 5. The human gate marker.  Exit 0 only on real, separately adjudicated codings.
# --------------------------------------------------------------------------- #
if [ "$human_present" -eq 0 ]; then
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
  printf '%s\n' \
    "FAIL $ABSENT_DIAGNOSTIC: no human pilot exists -- two independent human codings in $SUBMISSION_STORE and a separate human adjudication in $ADJUDICATION_STORE are required; the harness fabricates neither" >&2
  printf '%s machinery_green=1 human_pilot_performed=false\n' "$ABSENT_TOKEN"
  printf '%s human=%s\n' "$MACHINERY_MARKER" "$ABSENT_TOKEN"
  exit "$ABSENT_EXIT"
fi

if [ "$(battery_human_flag "$BATTERY")" != "true" ]; then
  printf 'FAIL %s: a human pilot exists but the tracked battery still records human_pilot_performed=false; regenerate it once with M207_S02_WRITE_BATTERY=1\n' \
    "$ABSENT_DIAGNOSTIC" >&2
  exit "$FAIL_EXIT"
fi

human_verify_status=0
if uv run python scripts/m207_s02_pilot.py check >"$stage_log" 2>&1; then
  human_verify_status=0
else
  human_verify_status=$?
fi
sed 's/^/    /' "$stage_log"
if [ "$human_verify_status" -ne 0 ]; then
  printf '%s\n' '[m207-s02] FAILED -- the verifier rejected the human pilot contour' >&2
  exit "$FAIL_EXIT"
fi
if ! grep -q "$HUMAN_DATA_MARKER" "$stage_log"; then
  printf 'FAIL %s: the verifier did not report human data present after a green human pilot\n' \
    "$ABSENT_DIAGNOSTIC" >&2
  exit "$FAIL_EXIT"
fi

printf '%s\n' "$MARKER"
