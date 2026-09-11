#!/usr/bin/env bash
# Host-safe S07 T04 verifier. Single executable command, no corpus walk.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s07_evidence_verify.py --check --write-battery
uv run python scripts/test_m204_s07_evidence_verify.py
uv run python scripts/test_m204_s07_c4_run.py
uv run python scripts/test_m204_s07_governor_repeat.py
uv run python scripts/test_m204_s06_evidence_verify.py
bash scripts/m204_s05_verify.sh
uv run ruff format --check scripts/m204_s07_evidence_verify.py scripts/test_m204_s07_evidence_verify.py
uv run ruff check scripts/m204_s07_evidence_verify.py scripts/test_m204_s07_evidence_verify.py scripts/m204_s07_c4_run.py
cargo fmt --all --check
cargo check --workspace --offline
uv run python scripts/m204_s07_evidence_verify.py --check --write-battery
printf '%s\n' S07_T04_VERIFY_OK
