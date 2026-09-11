#!/usr/bin/env bash
# M204 S04 bounded verifier. Domain behavior remains in the Rust CLI/tests.
set -euo pipefail
cd "$(dirname "$0")/.."

bin=(cargo run -p ln-consultant-parser --offline --quiet --bin npa-contour-diagnostics --)
tmp="$(mktemp -d "${TMPDIR:-/tmp}/m204-s04.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
consultant="$tmp/consultant"
garant="$tmp/garant"
out="$tmp/receipt.jsonl"
mkdir -p "$consultant" "$garant"
printf '%s' '<not-wordml/>' > "$consultant/law_2024-01.xml"
printf '%s' '<second/>' > "$consultant/law_2024-02.xml"

# Generate a bounded receipt, then exercise the real check/exit-code contract.
"${bin[@]}" --root "$consultant" --garant-root "$garant" --out "$out" --limit 2 --jobs 2 --label s04-verify
for marker in \
  '"schema":"npa-contour-diagnostics/v2"' \
  '"parser_revision":"m204-s04-c4-contour-v1"' \
  '"inventory_digest":"sha256:' \
  '"record_kind":"canonical_payload"' \
  '"record_kind":"operational_envelope"' \
  '"block_presence"' \
  '"lawref_capture_presence"' \
  '"identity_binding_not_measured"' \
  '"legal_marker_presence"'; do
  grep -Fq "$marker" "$out"
done
! grep -Eq 'not-wordml|<second' "$out"
"${bin[@]}" --root "$consultant" --garant-root "$garant" --out "$out" --limit 2 --jobs 2 --label changed-label --check

# Payload-only mutation keeps the binding equal and must be classified as semantic drift.
sed -i 's/"files":2/"files":3/g' "$out"
if "${bin[@]}" --root "$consultant" --garant-root "$garant" --out "$out" --limit 2 --jobs 2 --check; then
  echo 'expected semantic drift exit 6' >&2
  exit 1
else
  [[ "$?" -eq 6 ]]
fi

# Byte mutation changes the inventory binding and is therefore incomparable.
"${bin[@]}" --root "$consultant" --garant-root "$garant" --out "$out" --limit 2 --jobs 2
printf '%s' '<mutated/>' > "$consultant/law_2024-01.xml"
if "${bin[@]}" --root "$consultant" --garant-root "$garant" --out "$out" --limit 2 --jobs 2 --check; then
  echo 'expected incomparable input exit 7' >&2
  exit 1
else
  [[ "$?" -eq 7 ]]
fi

printf '%s' '{}' > "$out"
if "${bin[@]}" --root "$consultant" --garant-root "$garant" --out "$out" --limit 2 --jobs 2 --check; then
  echo 'expected incomparable baseline exit 7' >&2
  exit 1
else
  [[ "$?" -eq 7 ]]
fi
rm "$out"
if "${bin[@]}" --root "$consultant" --garant-root "$garant" --out "$out" --limit 2 --jobs 2 --check; then
  echo 'expected missing baseline exit 8' >&2
  exit 1
else
  [[ "$?" -eq 8 ]]
fi

# Existing S03 verifier owns the immutable M203 pin boundary and its corpus checks.
bash scripts/m204_s03_verify.sh
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
cargo fmt --all --check
cargo check --workspace --offline
printf '%s\n' S04_VERIFY_OK
