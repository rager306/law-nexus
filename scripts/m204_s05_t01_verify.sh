#!/usr/bin/env bash
# Host-safe S05 T01 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."
cargo test -p ln-consultant-parser --offline --test acceptance_retry_contract
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
cargo fmt --all --check
cargo check --workspace --offline
echo S05_T01_VERIFY_OK
