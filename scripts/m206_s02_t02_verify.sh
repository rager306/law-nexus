#!/usr/bin/env bash
# Fail-closed design-only contract verify for M206/S02 adoption state.
# Scope: repository-local document checks only. No runtime, deps, corpus, network.
# Positive contract: every required marker must be present.
# Negative mutations: contradicting runtime/adoption claims, broken deferred
# list, and F09/Reject conflation MUST be rejected (non-zero).
set -u

DOC="prd/architecture/m206-s02-adoption-state.md"

fail() { echo "FAIL: $*"; exit 1; }

# --- positive + forbidden-claims checks against a given file ---
check_file() {
  local f="$1"
  [ -f "$f" ] || { echo "FAIL: missing $f"; return 1; }

  local m
  while IFS= read -r m; do
    [ -n "$m" ] || continue
    grep -qF -- "$m" "$f" || { echo "FAIL: missing required marker: $m"; return 1; }
  done <<'MARKERS'
scope: RC28-F09, RC28-F10
classification: design-only
runtime_demo: not-proven
runtime_stop_active: true
human_adoption: pending
requirement_status_effect: unchanged
review_disposition_effect: unchanged
selected_already: G01, G02, G14
must_not_select: G06, G07, G12, G13
resume: new explicit source-bound owner admission and separate runtime replan
04fd05a2-338f-45af-a1cc-13501717dc53
F09-independent-sentences
F09-incomplete-tail
F09-boundaries
F09-refused-token-only
F09-identical-origins
F09-overlap
F09-order
F10-original-spans
MARKERS

  # full deferred list preserved verbatim (G01/G02/G14 selected; G14 not in list)
  grep -qF 'G03,G04,G05,G06,G07,G08,G09,G10,G11,G12,G13,G15,G16' "$f" || {
    echo "FAIL: deferred gate list G03..G16 not preserved verbatim"; return 1; }

  # forbidden contradicting claims (gate flag: additive claims must be rejected)
  if grep -Eq 'runtime_demo:[[:space:]]*(proven|passed|ok)' "$f"; then
    echo "FAIL: contradicting runtime_demo claim present"; return 1; fi
  if grep -Eq 'human_adoption:[[:space:]]*(accepted|approved|granted)' "$f"; then
    echo "FAIL: contradicting human_adoption claim present"; return 1; fi
  # F09 stays pending; it must NOT be affirmatively attributed to the owner
  # Reject (F06/F10 only). Documented negations ("not a new F09 Reject",
  # "no new owner Reject for F09") are allowed; line wrapping is handled by
  # joining the text before matching.
  local joined stripped
  joined=$(tr '\n' ' ' < "$f")
  # strip the documented negation phrases first, then look for any remaining
  # affirmative F09-reject attribution
  stripped=$(printf '%s' "$joined" | sed -e 's/not a new F09 Reject//g' -e 's/no new owner Reject for F09//g')
  if echo "$stripped" | grep -Eiq 'Reject[^.]{0,30}F09|F09[^.]{0,30}Reject'; then
      echo "FAIL: F09 affirmatively attributed to owner Reject (covers F06/F10 only)"; return 1; fi
  # must_not_select gates must not appear as selected
  if grep -Eq 'selected[^:]*:.*G(06|07|12|13)' "$f"; then
    echo "FAIL: must_not_select gate appears as selected"; return 1; fi
  return 0
}

# --- negative mutation runner: mutation MUST be rejected ---
rejects() {
  local label="$1" expr="$2" tmp
  tmp=$(mktemp) || fail "mktemp"
  sed "$expr" "$DOC" > "$tmp" 2>/dev/null || { rm -f "$tmp"; fail "sed failed: $label"; }
  if check_file "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    fail "mutation NOT rejected: $label"
  fi
  rm -f "$tmp"
  echo "ok: mutation rejected: $label"
}

# --- main ---
if [ "${1:-}" = "--check-file" ]; then
  check_file "$2"
  exit $?
fi

[ -f "$DOC" ] || fail "missing $DOC"
check_file "$DOC" || exit 1
echo "ok: positive contract verified for $DOC"

rejects "additive runtime_demo: proven" \
  's/\*\*runtime_demo: not-proven\*\*/&\nruntime_demo: proven/'
rejects "additive human_adoption: accepted" \
  's/\*\*human_adoption: pending\*\*/&\nhuman_adoption: accepted/'
rejects "deferred list broken (G16 dropped)" \
  's/G16/GX16/'
rejects "F09 conflated with owner Reject" \
  '$a\F09 owner Reject: recorded'
rejects "must_not_select gate selected (G07)" \
  's/selected_already: G01, G02, G14/selected_already: G01, G02, G07, G14/'

echo "M206_S02_T02_VERIFY_OK"
exit 0
