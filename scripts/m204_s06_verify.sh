#!/usr/bin/env bash
# M204 S06 bounded evidence verifier; no corpus walk or lifecycle mutation.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s06_evidence_verify.py --check
uv run python scripts/m204_s06_c4_run.py --verify-receipt prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json
bash scripts/m204_s05_verify.sh
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
cargo test -p ln-consultant-parser --offline --test acceptance_retry_contract
cargo fmt --all --check
cargo check --workspace --offline
uv run python scripts/m204_s06_evidence_verify.py --check --write-battery
printf '%s\n' S06_VERIFY_OK
