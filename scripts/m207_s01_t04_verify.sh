#!/usr/bin/env bash
# Offline closeout chain for the M207 S01 annotation-pilot boundary (T04).
#
# Runs the three per-task gates, the slice verifier, the adversarial subprocess
# suite, the formatter/linter and the ADR conformance check, then checks the
# tracked battery against the recorded per-check results.  The final line is the
# sole success marker: M207_S01_VERIFY_OK.  Nothing here reaches the network,
# mutates git state, starts a model, or reads a human coding.
#
# The chain is READ-ONLY with respect to the repository: it never writes the
# tracked battery, so it is safe to run inside the host's source-integrity
# window.  The battery is regenerated once by an explicit opt-in before host
# verification:
#
#   M207_S01_WRITE_BATTERY=1 bash scripts/m207_s01_t04_verify.sh
#
# Any other invocation compares the freshly assembled payload byte-for-byte
# with prd/migration/rust-evidence/m207-s01-battery.json and fails closed with
# BATTERY_STALE when they differ.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

readonly MARKER="M207_S01_VERIFY_OK"
readonly BATTERY="prd/migration/rust-evidence/m207-s01-battery.json"
readonly CHECKS=(
  scripts/m207_s01_schemas.py
  scripts/m207_s01_select_cases.py
  scripts/m207_s01_prompt_packet.py
  scripts/m207_s01_pilot.py
  scripts/test_m207_s01_pilot.py
)

results="$(mktemp -t m207-s01-results-XXXXXX)"
trap 'rm -f "$results"' EXIT

failed=0

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
}

printf '%s\n' '[m207-s01] offline closeout chain'
run gate-schemas uv run python scripts/m207_s01_schemas.py check
run gate-select-cases uv run python scripts/m207_s01_select_cases.py check
run gate-prompt-packet uv run python scripts/m207_s01_prompt_packet.py check
run verifier-pilot uv run python scripts/m207_s01_pilot.py check
run adversarial-suite uv run python scripts/test_m207_s01_pilot.py
run ruff-format-check uv run ruff format --check "${CHECKS[@]}"
run ruff-lint uv run ruff check "${CHECKS[@]}"
run adr-conformance uv run python scripts/verify-adr-conformance.py

if [ "$failed" -ne 0 ]; then
  printf '%s\n' '[m207-s01] FAILED -- see the failing check above' >&2
  exit 1
fi

battery_args=(--results "$results" --out "$BATTERY")
if [ "${M207_S01_WRITE_BATTERY:-0}" = "1" ]; then
  battery_args+=(--write)
fi
uv run python scripts/m207_s01_pilot.py battery "${battery_args[@]}"

printf '%s\n' "$MARKER"
