#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Bounded replay only; T02's recorded execution is the sole corpus-bound action.
bash scripts/m204_s12_t01_verify.sh
bash scripts/m204_s12_t02_verify.sh
bash scripts/m204_s11_t01_verify.sh

uv run python scripts/m204_s12_hard_block.py compose
uv run python scripts/test_m204_s12_hard_block.py
uv run python scripts/m204_s12_hard_block.py verify
uv run python scripts/m204_s12_failure_probe.py verify
uv run ruff check scripts/m204_s12_hard_block.py scripts/test_m204_s12_hard_block.py scripts/m204_s12_failure_probe.py scripts/test_m204_s12_failure_probe.py
uv run ruff format --check scripts/m204_s12_hard_block.py scripts/test_m204_s12_hard_block.py scripts/m204_s12_failure_probe.py scripts/test_m204_s12_failure_probe.py
cargo fmt --all --check
cargo check --workspace --offline
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
printf '%s\n' S12_VERIFY_OK
