#!/usr/bin/env bash
set -euo pipefail

# S13/T01 is a bounded source-binding proof: it never walks the corpus or reads .gsd.
uv run python scripts/m204_s13_source_binding.py compose
uv run python scripts/test_m204_s13_source_binding.py
uv run python scripts/m204_s13_source_binding.py verify
uv run ruff check scripts/m204_s13_source_binding.py scripts/test_m204_s13_source_binding.py
uv run ruff format --check scripts/m204_s13_source_binding.py scripts/test_m204_s13_source_binding.py
printf '%s\n' 'S13_T01_BINDING_OK'
