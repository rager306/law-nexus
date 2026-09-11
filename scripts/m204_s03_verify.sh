#!/usr/bin/env bash
# M204 S03 bounded end-to-end verifier. Fails closed on missing corpus or evidence.
set -euo pipefail
cd "$(dirname "$0")/.."

consultant_root="consru_export/consru_export/exports"
garant_root="law-source/garant"
out="prd/migration/rust-evidence"
[[ -d "$consultant_root" ]] || { echo "missing consultant corpus: $consultant_root" >&2; exit 4; }
[[ -d "$garant_root" ]] || { echo "missing Garant corpus: $garant_root" >&2; exit 4; }
[[ -n "$(find "$consultant_root" -type f -name '*.xml' -print -quit)" ]] || { echo "consultant corpus has no XML files" >&2; exit 4; }
[[ -n "$(find "$garant_root" -type f \( -name '*.xml' -o -name '*.odt' \) -print -quit)" ]] || { echo "Garant corpus has no supported files" >&2; exit 4; }

cargo test -p ln-consultant-parser --offline --test corpus_sample_contract --test gold_ladder_cli_contract --test gold_ladder_contract --test contour_diagnostics_contract
cargo test -p ln-consultant-parser --offline --test corpus_manifest_contract --test gold_coding_contract --test promotion_gate_contract

cargo run -p ln-consultant-parser --offline --bin npa-gold-ladder -- \
  --root "$consultant_root" --garant-root "$garant_root" --out "$out" --seed 20308 --check

for rung in 100 400 800; do
  test -s "$out/m204-s02-c5-gold-manifest-$rung.json"
done
for artifact in \
  m204-s02-c5-coding.jsonl \
  m204-s02-c5-agreement.jsonl \
  m204-s02-c5-quality-receipts.jsonl \
  m204-s03-sample-leakage.json; do
  test -s "$out/$artifact"
done

grep -q '"schema":"m204-s03-sample-leakage/v1"' "$out/m204-s03-sample-leakage.json"
grep -q '"seed":20308' "$out/m204-s03-sample-leakage.json"
grep -q '"not_year_type_stratified":true' "$out/m204-s03-sample-leakage.json"
grep -q '"collapsed_editions":30625' "$out/m204-s03-sample-leakage.json"
grep -q '"collapsed_families":123' "$out/m204-s03-sample-leakage.json"
grep -q 'not a Work-family holdout' "$out/m204-s03-sample-leakage.json"
grep -q 'C2 reuse is not independent evaluation' "$out/m204-s03-sample-leakage.json"

# Frozen M203 evidence is an immutable regression boundary, not a regeneration target.
expected_m203="ca3287bfdf20e326de24eeb2cddf88da1a60845ac4535ec58a4e41ad5f60f993  prd/migration/rust-evidence/m203-s08-c2-bounded-manifest.json
37c85ca480884717199453abd2ccc148b32d5011b194f160263764f469bbf388  prd/migration/rust-evidence/m203-s08-c3-holdout-manifest.json
09488919de24a26220b04f8e4bde4516bc6ad4aa41e983045866c517e21bb5ce  prd/migration/rust-evidence/m203-s08-c4-full-diagnostics.jsonl
5e839c9bb44718b1a60856e6e9ce96104b447c4b15f014e74cefb66c264623f4  prd/migration/rust-evidence/m203-s08-c5-gold-manifest-100.json
353c690220696bf449bd54ba46c3e006e22ef92cf05a0faae2517892e7723578  prd/migration/rust-evidence/m203-s08-c5-gold-manifest-400.json
be2e47b56f2b6db476c7f156dd6aa58d51b1d05eb54432fe93c9a91917ee6d60  prd/migration/rust-evidence/m203-s08-c5-gold-manifest-800.json
13413c6f6c522b7ca53578422ab6fc3dca0cb287406e0810ba7140d8dc064445  prd/migration/rust-evidence/m203-s08-c5-coding.jsonl
98fa36fbb91aa520feaf0d9fed9c2bdbb0ca30d886dc44da42b053edc9e31b70  prd/migration/rust-evidence/m203-s08-c5-agreement.jsonl
a4ada4cdfeaf1ede0b8514bfd759f8ed396e84b161d6c283fda21ca26e4807c4  prd/migration/rust-evidence/m203-s08-quality-receipts.jsonl
e41e305ff0fd955f18b28f6a56556660e6a34bf97c19970dfccd7882fc94813f  prd/migration/rust-evidence/m203-s08-ledger-events.jsonl
528599a338f6fc2428a9ade3f3ad3c28a9f702b8344fe1b38e9dd3d89d035493  prd/migration/rust-evidence/m203-s08-perf-receipts.jsonl"
actual_m203="$(sha256sum \
  prd/migration/rust-evidence/m203-s08-c2-bounded-manifest.json \
  prd/migration/rust-evidence/m203-s08-c3-holdout-manifest.json \
  prd/migration/rust-evidence/m203-s08-c4-full-diagnostics.jsonl \
  prd/migration/rust-evidence/m203-s08-c5-gold-manifest-100.json \
  prd/migration/rust-evidence/m203-s08-c5-gold-manifest-400.json \
  prd/migration/rust-evidence/m203-s08-c5-gold-manifest-800.json \
  prd/migration/rust-evidence/m203-s08-c5-coding.jsonl \
  prd/migration/rust-evidence/m203-s08-c5-agreement.jsonl \
  prd/migration/rust-evidence/m203-s08-quality-receipts.jsonl \
  prd/migration/rust-evidence/m203-s08-ledger-events.jsonl \
  prd/migration/rust-evidence/m203-s08-perf-receipts.jsonl)"
[[ "$actual_m203" == "$expected_m203" ]] || { echo "frozen M203 evidence changed" >&2; diff -u <(printf '%s\n' "$expected_m203") <(printf '%s\n' "$actual_m203") >&2 || true; exit 5; }

cargo fmt --all --check
cargo check --workspace --offline
bash scripts/m204_s02_t01_verify.sh
printf '%s\n' S03_VERIFY_OK
