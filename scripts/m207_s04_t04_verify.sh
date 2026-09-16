#!/usr/bin/env bash
# Offline closeout chain for the M207 S04 operational contour (T04).
#
# WHAT THIS CHAIN IS, AND WHAT ITS MARKER MEANS
#
#   * every row below is an integrity check over the frozen S04 surface: the frozen schema
#     document, the C4 operational receipt and its attempt record, the promotion verdict,
#     the S03 isolation state, the HOLD pins and the repository hygiene checks;
#   * `M207_S04_VERIFY_OK` means **the integrity battery ran and every check passed**.  It is
#     NOT a C4 pass, NOT operational acceptance, NOT an independently measured rate, NOT gold
#     and NOT a requirement closure.  The C4 attempt this chain witnesses is published
#     `non-pass` by the frozen M204/S06 acceptance rule (a 387 s walk under a 3600 s budget is
#     a short walk, not an acceptance), and the promotion verdict stays `none` with
#     `classification = not-authorized`.  S03 rates stay `not-measured`;
#   * there is no human half.  S04 runs no pilot, so this chain never exits 3 and never claims
#     human data: the human gate belongs to S01/S02/S03 and stays exactly where it was.
#
# MACHINE HALF (the eight frozen battery rows, in order)
#
#   * `s04_schemas` -- `scripts/m207_s04_schemas.py check` (marker `M207_S04_SCHEMAS_OK`);
#   * `s04_c4_receipt` -- `scripts/m207_s04_c4_run.py check` (marker
#     `M207_S04_C4_RECEIPT_OK`).  It validates the receipt against the frozen contract and the
#     live tree -- integrity and honest publication, never acceptance;
#   * `s04_hostile_suite` -- `scripts/test_m207_s04_pilot.py` (`OK`): the adversarial suite
#     over the real CLI;
#   * `s04_machinery_verifier` -- `scripts/m207_s04_pilot.py check` (marker
#     `M207_S04_PROMOTION_NONE_OK`).  It re-derives the promotion verdict from the receipt's
#     own terminal facts and re-proves the S03 isolation state.  It can never print the
#     integrity marker, and this chain requires that;
#   * `s03_regression` -- the S03 closeout chain as a real subprocess.  Exit 0 (a human pilot
#     happened) and exit 3 (honest `HUMAN_PILOT_ABSENT`) are both green, anything else is
#     `S03_REGRESSION_FAILED`.  The row records exit_code 0 because the *boundary* is green;
#     the accepted child exits are named in the row's command column, so a reader of the
#     tracked battery never mistakes a normalized 3 for a raw 0;
#   * `ruff_format`, `ruff_check`, `adr_conformance` -- the S04 Python surface and
#     `scripts/verify-adr-conformance.py` (`"finding_count": 0`).
#
#   A marker is required, not merely an exit code: a gate that exits 0 without printing its own
#   marker is `SUBCLI_FAILURE`.
#
# CHAIN-LEVEL PINS (deliberately NOT battery rows)
#
#   * the 180-fragment seed count, and the three frozen HOLD-pin re-tests the protocol names
#     (`cargo test -p ln-kb-ontology --offline --test r035_proof_gate`,
#     `cargo test -p ln-temporal --offline --test r070_proof_gate`,
#     `cargo test -p ln-decode --offline --test npa_lawref_sample_contract`).  A green pin is
#     not a status change: R035 and R070 stay HOLD and R074 is untouched (no `crates/**` file
#     changes, D487).  The `r035`/`r070` rows duplicate the S03 chain's own extras on purpose:
#     the protocol says T04 runs them, and a named row is auditable where a nested subprocess
#     is not;
#   * `cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract` -- the
#     offline contour contract of the binary the C4 attempt ran;
#   * `s03_battery_flag` -- the S03 battery is re-read and must still record
#     `human_pilot_performed = false` (its digest is printed for the durable log);
#   * `c4_receipt_facts` / `c4_acceptance_basis` -- the receipt's own process facts (argv
#     digest, binary and contract digests, corpus counts, terminal outcome, budget, duration,
#     log hashes) and the verifier's recomputed acceptance basis, printed as compact
#     observation lines.  They are projections of what the rows above already proved, never a
#     second gate and never a second verdict.
#
# FAIL-CLOSED GUARDS
#
#   * the chain takes NO arguments: it never accepts `--root`, because a foreign forged tree
#     with a self-consistent store would otherwise reach the marker.  The root is derived from
#     BASH_SOURCE;
#   * the battery opt-in is read once and then *unset together with the S03 and S02 opt-ins*:
#     no child process (the hostile suite, a gate, the S03 chain) may inherit a mode-switching
#     variable, and the mandatory post-write read-only pass below can never silently rewrite
#     the tracked artifact -- which would make `BATTERY_STALE` unobservable (write mode never
#     fails).  Only the single authorized battery command receives `--write`;
#   * the chain is READ-ONLY with respect to the tracked battery unless
#     `M207_S04_WRITE_BATTERY=1` is set, which regenerates
#     `prd/migration/rust-evidence/m207-s04-battery.json` exactly once, before host
#     verification (D473), and is then confirmed by a read-only run that must stay current.
#     Any other invocation compares the freshly assembled payload byte-for-byte with the
#     tracked file and fails closed with `BATTERY_STALE`;
#   * `scripts/m207_s04_pilot.py battery` refuses `--write` without the opt-in
#     (`AUTHORITY_CLAIM`), refuses a result table whose check set or row shape drifts from the
#     frozen chain (`SCHEMA_KEY_DRIFT`), refuses a non-green row (`SUBCLI_FAILURE`), a frozen
#     source whose digest moved (`FROZEN_SOURCE_DRIFT`) and a missing pin (`MISSING_ARTIFACT`).
set -euo pipefail

readonly MARKER="M207_S04_VERIFY_OK"
readonly FAIL_EXIT=1
readonly ABSENT_EXIT=3

# The closing chain never accepts a foreign root: a forged tree would otherwise be
# indistinguishable from the repository.  Named, fail-closed.
if [ "$#" -ne 0 ]; then
  printf 'FAIL UNSAFE_PATH: the closing chain takes no arguments; --root is refused and the repository root comes from BASH_SOURCE\n' >&2
  exit "$FAIL_EXIT"
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

readonly EVIDENCE="prd/migration/rust-evidence"
readonly BATTERY="$EVIDENCE/m207-s04-battery.json"
readonly S03_BATTERY="$EVIDENCE/m207-s03-battery.json"

readonly FRAGMENT_COUNT_CHECK='test "$(find crates/ln-decode/tests/fixtures/npa-lawref -name "*.txt" | wc -l | tr -d " ")" = 180'
readonly CARGO_NPA_CONTRACT="cargo test -p ln-decode --offline --test npa_lawref_sample_contract"
readonly CARGO_R035="cargo test -p ln-kb-ontology --offline --test r035_proof_gate"
readonly CARGO_R070="cargo test -p ln-temporal --offline --test r070_proof_gate"
readonly CARGO_CONTOUR="cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract"

# The verifier's own recomputed acceptance basis, trimmed to the receipt facts this slice
# publishes.  Read from the verdict the machinery verifier already proved; never a second
# verdict and never the published claim.
readonly C4_SUMMARY_CMD='uv run python scripts/m207_s04_pilot.py check | grep -oE "\"(receipt|acceptance_basis)\":\{[^}]*\}"'

# The receipt's own process facts, as the C4 gate validated them: argv digest, binary and
# contract digests, corpus counts, terminal outcome, budget, duration and log hashes.  An
# observation line for the durable log, never a second gate.  The receipt path is the frozen
# one; the C4 gate already validates it against the contract and the live tree.
readonly C4_FACTS_CMD='uv run python -c "import json,sys
d=json.load(open(sys.argv[1], encoding=\"utf-8\"))
b=d[\"build_inputs\"]; c=d[\"corpus\"]; g=d[\"logs\"]; i=d[\"immutable_attempt_identity\"]; t=d[\"terminal\"]
print(\"c4_receipt attempt=%s argv_sha256=%s binary_sha256=%s contract_sha256=%s consultant_xml=%d garant_files=%d terminal=%s/%s budget_seconds=%d duration_ms=%d source_revision=%s stdout_sha256=%s stderr_sha256=%s\" % (d[\"attempt_id\"], i[\"argv_sha256\"], b[\"binary_sha256\"], b[\"contract_sha256\"], c[\"consultant_xml_count\"], c[\"garant_file_count\"], t[\"outcome\"], t[\"exit_code\"], d[\"budget_seconds\"], d[\"duration_ms\"], d[\"source_revision\"], g[\"stdout_sha256\"], g[\"stderr_sha256\"]))" prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json'

# The S03 battery stays current and must still record human_pilot_performed = false.
readonly S03_BATTERY_FLAG_CMD="uv run python -c 'import hashlib,json,pathlib; p=pathlib.Path(\"$S03_BATTERY\"); d=json.loads(p.read_text(encoding=\"utf-8\")); f=d.get(\"human_pilot_performed\"); print(\"s03_battery human_pilot_performed=%s sha256=%s\" % (f, hashlib.sha256(p.read_bytes()).hexdigest())); raise SystemExit(0 if f is False else 1)'"

# The Python surface the formatter and the linter cover (the bash chain is not Python; the
# S02/S03 scripts are covered by their own chains).
readonly CHECKS=(
  scripts/m207_s04_schemas.py
  scripts/m207_s04_c4_run.py
  scripts/m207_s04_pilot.py
  scripts/test_m207_s04_pilot.py
)

results="$(mktemp -t m207-s04-results-XXXXXX)"
stage_log="$(mktemp -t m207-s04-stage-XXXXXX)"
trap 'rm -f "$results" "$stage_log"' EXIT

# Read the D473 opt-in once and keep the ambient environment clean for every child process;
# every write flag is cleared so a read-only pass stays read-only.  Only the single authorized
# battery command below is handed `--write`.
write_battery=0
if [ "${M207_S04_WRITE_BATTERY:-0}" = "1" ]; then
  write_battery=1
fi
unset M207_S04_WRITE_BATTERY
unset M207_S03_WRITE_BATTERY
unset M207_S02_WRITE_BATTERY

failed=0

# Battery rows: `id<TAB>status<TAB>durationMs<TAB>command`, in a fixed order.  The command
# column must be byte-stable across runs: the tracked battery is compared byte-for-byte, so no
# absolute or temporary path may reach it.
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
  printf '[m207-s04] %-22s exit=%d %7dms %s\n' \
    "$id" "$status" "$(((end - start) / 1000000))" "$command"
  if [ "$status" -eq 0 ]; then
    tail -n 2 "$stage_log" | sed 's/^/    /'
  else
    tail -n 25 "$stage_log" | sed 's/^/    /'
  fi
}

# A battery row whose gate must also print the marker it claims: a zero exit without the marker
# is a contract failure, not a success.
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
  printf '[m207-s04] %-22s exit=%d %7dms %s\n' \
    "$id" "$status" "$(((end - start) / 1000000))" "$command"
  tail -n 2 "$stage_log" | sed 's/^/    /'
}

# The S03 boundary is green on exit 0 (human pilot performed) and on exit 3 (honest absence);
# the row records the boundary verdict, and its command column names the accepted child exits.
# Anything else is S03_REGRESSION_FAILED.
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
    printf '[m207-s04] %-22s exit=%d accepted (0 or 3 = green boundary) %7dms\n' \
      "$id" "$status" "$(((end - start) / 1000000))"
    printf '%s\t0\t%d\t%s\n' "$id" "$(((end - start) / 1000000))" "$command" >>"$results"
  else
    printf 'FAIL S03_REGRESSION_FAILED: %s exited %d; only 0 (human pilot performed) and 3 (HUMAN_PILOT_ABSENT) are green\n' \
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
  printf '[m207-s04] %-22s exit=%d %7dms %s\n' \
    "$id" "$status" "$(((end - start) / 1000000))" "$command"
  if [ "$status" -eq 0 ]; then
    tail -n 2 "$stage_log" | sed 's/^/    /'
  else
    tail -n 25 "$stage_log" | sed 's/^/    /'
  fi
}

printf '%s\n' '[m207-s04] offline S04 closeout chain (integrity battery; not a C4 pass)'

# --------------------------------------------------------------------------- #
# 1. Machinery: the eight frozen battery rows.  Every id below is one of the ids
#    the verifier's frozen chain declares; battery mode refuses any other set.
# --------------------------------------------------------------------------- #
run_marker s04_schemas 'M207_S04_SCHEMAS_OK' \
  uv run python scripts/m207_s04_schemas.py check
run_marker s04_c4_receipt 'M207_S04_C4_RECEIPT_OK' \
  uv run python scripts/m207_s04_c4_run.py check
run_marker s04_hostile_suite '^OK$' \
  uv run python scripts/test_m207_s04_pilot.py
run_marker s04_machinery_verifier 'M207_S04_PROMOTION_NONE_OK' \
  uv run python scripts/m207_s04_pilot.py check
run_regression s03_regression bash scripts/m207_s03_t06_verify.sh
run ruff_format uv run ruff format --check "${CHECKS[@]}"
run ruff_check uv run ruff check "${CHECKS[@]}"
run_marker adr_conformance '"finding_count": ?0' \
  uv run python scripts/verify-adr-conformance.py

# --------------------------------------------------------------------------- #
# 2. Chain-level pins (not battery rows): the frozen HOLD re-tests, the offline
#    contour contract, the seed count and the S03 battery flag.  A green pin is
#    not a status change.
# --------------------------------------------------------------------------- #
run_extra fragment-count "$FRAGMENT_COUNT_CHECK" bash -c "$FRAGMENT_COUNT_CHECK"
run_extra cargo-npa-lawref-contract "$CARGO_NPA_CONTRACT" \
  cargo test -p ln-decode --offline --test npa_lawref_sample_contract
run_extra cargo-r035-proof-gate "$CARGO_R035" \
  cargo test -p ln-kb-ontology --offline --test r035_proof_gate
run_extra cargo-r070-proof-gate "$CARGO_R070" \
  cargo test -p ln-temporal --offline --test r070_proof_gate
run_extra cargo-contour-contract "$CARGO_CONTOUR" \
  cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
run_extra s03-battery-flag "$S03_BATTERY_FLAG_CMD" bash -c "$S03_BATTERY_FLAG_CMD"
run_extra c4-acceptance-basis "$C4_SUMMARY_CMD" bash -c "$C4_SUMMARY_CMD"
run_extra c4-receipt-facts 'uv run python -c <receipt facts> prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json (argv/binary/contract digests, corpus counts, terminal, budget, duration, log hashes)' \
  bash -c "$C4_FACTS_CMD"

if [ "$failed" -ne 0 ]; then
  printf '%s\n' '[m207-s04] FAILED -- the integrity contour is red; see the failing check above' >&2
  exit "$FAIL_EXIT"
fi

# --------------------------------------------------------------------------- #
# 3. Battery: assemble from the result table (write only under the D473 opt-in),
#    then confirm with a read-only pass that must stay current.  The opt-in was
#    unset at the top, so the confirmation run cannot silently rewrite anything.
# --------------------------------------------------------------------------- #
if [ "$write_battery" -eq 1 ]; then
  printf '%s\n' '[m207-s04] M207_S04_WRITE_BATTERY=1: regenerating the tracked battery once'
  # The opt-in was read once at the top and then unset, so the authorization is re-supplied
  # to this one command only: `--write` without M207_S04_WRITE_BATTERY=1 is refused by the
  # tool itself (AUTHORITY_CLAIM), and the read-only confirmation below still runs with a
  # clean environment.
  if ! M207_S04_WRITE_BATTERY=1 uv run python scripts/m207_s04_pilot.py battery \
    --results "$results" --out "$BATTERY" --write; then
    printf '%s\n' '[m207-s04] FAILED -- the authorized battery write failed' >&2
    exit "$FAIL_EXIT"
  fi
fi
battery_status=0
if uv run python scripts/m207_s04_pilot.py battery \
  --results "$results" --out "$BATTERY" >"$stage_log" 2>&1; then
  battery_status=0
else
  battery_status=$?
fi
if [ "$battery_status" -ne 0 ]; then
  sed 's/^/    /' "$stage_log"
  printf '%s\n' '[m207-s04] FAILED -- the tracked battery is stale or malformed; regenerate once with M207_S04_WRITE_BATTERY=1 before host verification' >&2
  exit "$FAIL_EXIT"
fi
if ! grep -q '^M207_S04_BATTERY_OK ' "$stage_log"; then
  printf '%s\n' '[m207-s04] FAILED -- the battery assembler exited 0 without printing M207_S04_BATTERY_OK' >&2
  exit "$FAIL_EXIT"
fi
sed 's/^/    /' "$stage_log"

# --------------------------------------------------------------------------- #
# 4. The integrity marker.  Printed last, and only after every row above passed.
# --------------------------------------------------------------------------- #
printf '%s\n' \
  '[m207-s04] the C4 attempt stays a published non-pass (short walk under the declared budget); promotion=none, classification=not-authorized, S03 rates not-measured'
printf '%s\n' \
  '[m207-s04] M207_S04_VERIFY_OK means the S04 integrity battery ran and every check passed: not a C4 pass, not operational acceptance and not an independently measured rate'
printf '%s\n' "$MARKER"
