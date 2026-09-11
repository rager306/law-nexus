#!/usr/bin/env bash
# M204 S05 bounded verifier. Domain stays in Rust; process checks stay in Python.
# Host-safe single command for slice closeout.
set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/m204_s05_t01_verify.sh
bash scripts/m204_s05_t02_verify.sh
bash scripts/m204_s04_verify.sh

# Frozen M203 evidence is an immutable regression boundary, never a regeneration target.
# Reuse the authoritative pin manifest owned by S03; this avoids a second, drifting hash list.
pin_manifest="$(mktemp "${TMPDIR:-/tmp}/m204-s05-pins.XXXXXX")"
trap 'rm -f "$pin_manifest"' EXIT
awk '
  /^expected_m203=/ { capture=1; sub(/^expected_m203="/, ""); }
  capture { sub(/"$/, ""); print; }
  capture && /perf-receipts\.jsonl"?$/ { exit }
' scripts/m204_s03_verify.sh > "$pin_manifest"
test -s "$pin_manifest"
sha256sum --check --strict "$pin_manifest"

# Explicitly reject zero-byte pins even if a future hash fixture is accidentally blank.
while IFS= read -r entry; do
  pin="${entry#*  }"
  test -s "$pin"
done < "$pin_manifest"

echo S05_VERIFY_OK
