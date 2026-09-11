#!/usr/bin/env bash
# Host-safe S05 T04 verifier. Single command, no nested quotes in the PLAN field.
set -euo pipefail
cd "$(dirname "$0")/.."

need=(
  prd/architecture/npa-corpus-control.yaml
  prd/architecture/review-cases/rc28-remediation-program.md
)
for rel in "${need[@]}"; do
  [[ -s "$rel" ]] || { echo "missing $rel" >&2; exit 1; }
done

python3 - <<'PY'
from pathlib import Path
control = Path("prd/architecture/npa-corpus-control.yaml").read_text()
program = Path("prd/architecture/review-cases/rc28-remediation-program.md").read_text()
needles = [
    ("npa-corpus-control.yaml", control, "acceptance"),
    ("npa-corpus-control.yaml", control, "contract_version"),
    ("rc28-remediation-program.md", program, "awaiting_disposition"),
]
for name, text, needle in needles:
    if needle not in text:
        raise SystemExit(f"{name} missing {needle}")
print("S05 T04 docs markers present")
PY

echo S05_T04_VERIFY_OK
