#!/usr/bin/env bash
# Serialized M204/S13 aggregate. Never composes or rewrites frozen evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s13_evidence_verify.py verify
bash scripts/m204_s13_t01_verify.sh
bash scripts/m204_s13_t02_verify.sh
bash scripts/m204_s07_verify.sh
bash scripts/m204_s07_t05_verify.sh
bash scripts/m204_s07_t06_verify.sh
uv run python scripts/m204_s12_hard_block.py verify
uv run python scripts/test_m204_s13_evidence_verify.py
uv run ruff check scripts/m204_s13_evidence_verify.py scripts/test_m204_s13_evidence_verify.py
uv run ruff format --check scripts/m204_s13_evidence_verify.py scripts/test_m204_s13_evidence_verify.py
cargo fmt --all --check
cargo check --workspace --offline
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
uv run python scripts/m204_s13_evidence_verify.py verify
printf '%s\n' S13_VERIFY_OK
