#!/usr/bin/env bash
# Host-safe S02 T01 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."
cargo test -p ln-consultant-parser --offline --test gold_ladder_contract
cargo test -p ln-consultant-parser --offline --test gold_coding_contract
cargo test -p ln-consultant-parser --offline --test promotion_gate_contract
cargo fmt --all --check
cargo check --workspace --offline
echo S02_T01_VERIFY_OK
