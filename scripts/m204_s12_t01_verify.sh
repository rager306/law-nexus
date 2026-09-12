#!/usr/bin/env bash
set -euo pipefail

# Bounded S12/T01 verifier: no corpus walk and no .gsd evidence reads.
cargo fmt --all --check
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
cargo test -p ln-consultant-parser --offline contour_diagnostics::failure_sidecar_tests
cargo check -p ln-consultant-parser --offline

help_output="$(cargo run -p ln-consultant-parser --offline --bin npa-contour-diagnostics -- --help)"
grep -F -- '--failures-out <path>' <<<"$help_output" >/dev/null

fixture='consru_export/consru_export/exports/s12-t01-fixture'
rm -rf "$fixture"
trap 'rm -rf "$fixture" /tmp/s12-t01-out.jsonl /tmp/s12-t01-failures.jsonl /tmp/s12-t01-baseline.jsonl /tmp/s12-t01-check-failures.jsonl' EXIT
mkdir -p "$fixture"
printf '%s' '<not-wordml/>' > "$fixture/malformed.xml"

cargo run -p ln-consultant-parser --offline --bin npa-contour-diagnostics -- \
  --root "$fixture" --jobs 1 --out /tmp/s12-t01-out.jsonl \
  --failures-out /tmp/s12-t01-failures.jsonl >/dev/null
[ "$(wc -l < /tmp/s12-t01-out.jsonl)" -eq 5 ]
grep -F '"record_kind":"failure"' /tmp/s12-t01-failures.jsonl >/dev/null
grep -F '"provider":"consultant"' /tmp/s12-t01-failures.jsonl >/dev/null
grep -F '"path":"consru_export/consru_export/exports/s12-t01-fixture/malformed.xml"' /tmp/s12-t01-failures.jsonl >/dev/null
grep -F '"class":"decode"' /tmp/s12-t01-failures.jsonl >/dev/null
cp /tmp/s12-t01-out.jsonl /tmp/s12-t01-baseline.jsonl
cargo run -p ln-consultant-parser --offline --bin npa-contour-diagnostics -- \
  --root "$fixture" --jobs 1 --check --out /tmp/s12-t01-baseline.jsonl \
  --failures-out /tmp/s12-t01-check-failures.jsonl >/dev/null
[ ! -e /tmp/s12-t01-check-failures.jsonl ]

printf '%s\n' 'S12_T01_SIDECAR_OK'
