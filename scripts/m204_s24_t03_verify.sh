#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
cd "$root"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
find prd/migration/rust-evidence -maxdepth 1 -type f -name 'm204-s[0-2][0-3]-*' -print0 \
  | sort -z \
  | xargs -0 sha256sum > "$tmp"

bash scripts/m204_s24_t01_verify.sh
uv run python scripts/m204_s24_battery.py check
uv run python scripts/test_m204_s24_liveness.py
uv run python scripts/m204_s23_c4_run.py --verify-receipt \
  prd/migration/rust-evidence/m204-s23-remediation-v2-c4-receipt.json \
  --require-operational-pass
uv run python scripts/m204_s22_liveness.py check
uv run ruff check scripts/m204_s24_battery.py scripts/test_m204_s24_liveness.py scripts/m204_s24_liveness.py
uv run ruff format --check scripts/m204_s24_battery.py scripts/test_m204_s24_liveness.py scripts/m204_s24_liveness.py
cargo test -p ln-consultant-parser --offline --locked -j 1 --test contour_diagnostics_contract

if ! cmp -s "$tmp" <(find prd/migration/rust-evidence -maxdepth 1 -type f -name 'm204-s[0-2][0-3]-*' -print0 | sort -z | xargs -0 sha256sum); then
  echo 'historical S07-S23 evidence changed during verification' >&2
  exit 1
fi

echo S24_T03_VERIFY_OK
