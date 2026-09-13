#!/usr/bin/env bash
set -euo pipefail

# T01 is fixture-only by contract: this verifier never launches a corpus walk.
uv run python scripts/test_m204_s23_c4_run.py
uv run ruff check scripts/m204_s23_c4_run.py scripts/test_m204_s23_c4_run.py
uv run ruff format --check scripts/m204_s23_c4_run.py scripts/test_m204_s23_c4_run.py
printf '%s\n' 'S23_T01_PREDICATE_OK' 'S23_T01_NEGATIVES_OK' 'S23_T01_NO_FULL_WALK_OK'
