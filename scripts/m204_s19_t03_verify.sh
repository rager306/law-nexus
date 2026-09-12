#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

census=prd/migration/rust-evidence/m204-s19-post-s18-validate-abort.json
manifest=prd/migration/rust-evidence/m204-s19-frozen-hashes.json
checker=scripts/m204_s19_loop_note.py
adversarial=scripts/test_m204_s19_validate_loop.py

# T03 is a fixed-census verifier: the checked census is never composed or replaced.
test -f "$census"
test -f "$manifest"
test -f "$checker"
test -f "$adversarial"

pins=(
  prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json
  prd/migration/rust-evidence/m204-s09-trigger-sql.json
  prd/migration/rust-evidence/m204-s12-validate-hard-block.json
  prd/migration/rust-evidence/m204-s12-frozen-hashes.json
  prd/migration/rust-evidence/m204-s15-requirement-class.json
  prd/migration/rust-evidence/m204-s15-frozen-hashes.json
  prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json
  prd/migration/rust-evidence/m204-s16-frozen-hashes.json
  prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json
  prd/migration/rust-evidence/m204-s17-frozen-hashes.json
  prd/migration/rust-evidence/m204-s18-post-s17-validate-loop.json
  prd/migration/rust-evidence/m204-s18-frozen-hashes.json
)

# Capture all immutable inputs before any subprocess. A changed input or a write is fatal.
before=$(sha256sum "$census" "$manifest" "${pins[@]}")
test "${#pins[@]}" -eq 12

# Explicit check mode only; compose is intentionally not called here.
uv run python scripts/m204_s19_loop_note.py check --root "$PWD" --census "$PWD/$census" --manifest "$PWD/$manifest"
uv run python -m unittest scripts/test_m204_s19_validate_loop.py

# Assert the manifest itself contains exactly the twelve expected predecessor paths.
uv run python - "$manifest" "${pins[@]}" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = [Path(value).as_posix() for value in sys.argv[2:]]
actual = [entry["path"] for entry in manifest["files"]]
if len(actual) != 12 or actual != expected or len(set(actual)) != 12:
    raise SystemExit("S19 predecessor manifest is not exactly twelve ordered pins")
PY

after=$(sha256sum "$census" "$manifest" "${pins[@]}")
test "$before" = "$after"
printf '%s\n' S19_T03_VERIFY_OK
