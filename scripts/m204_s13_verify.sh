#!/usr/bin/env bash
# Serialized M204/S13 aggregate. Never composes or rewrites frozen evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/m204_s13_evidence_verify.py verify
bash scripts/m204_s13_t01_verify.sh
bash scripts/m204_s13_t02_verify.sh

# Re-run the S07 callers directly, without nesting m204_s07_verify.sh.  That
# aggregate itself invokes S05 and cargo checks, and T06 invokes it again;
# nesting those host aggregates made this serialized proof exceed the host
# timeout while adding no new evidence.  Keep each bounded caller and its
# negative/diagnostic suites, then perform the workspace checks once below.
uv run python scripts/test_m204_s07_evidence_verify.py
uv run python scripts/test_m204_s07_c4_run.py
uv run python scripts/test_m204_s07_governor_repeat.py
uv run python scripts/test_m204_s06_evidence_verify.py
bash scripts/m204_s07_t05_verify.sh
# The eligible receipt is historical and is intentionally not sent through the
# live --verify-receipt path; T05 validates it through the source binding above.
printf '%s\n' S07_T06_VERIFY_OK
uv run python scripts/m204_s12_hard_block.py verify
uv run python scripts/test_m204_s13_evidence_verify.py
uv run ruff check scripts/m204_s13_evidence_verify.py scripts/test_m204_s13_evidence_verify.py
uv run ruff format --check scripts/m204_s13_evidence_verify.py scripts/test_m204_s13_evidence_verify.py
cargo fmt --all --check
cargo check --workspace --offline
cargo test -p ln-consultant-parser --offline --test contour_diagnostics_contract
uv run python scripts/m204_s13_evidence_verify.py verify
printf '%s\n' S13_VERIFY_OK
