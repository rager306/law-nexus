#!/usr/bin/env bash
# M204 S05 bounded verifier. Domain stays in Rust; process checks stay in Python.
# Host-safe single command for slice closeout.
set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/m204_s05_t01_verify.sh
bash scripts/m204_s05_t02_verify.sh
bash scripts/m204_s04_verify.sh

python3 - <<'PY'
from hashlib import sha256
from pathlib import Path
pins = [
    "prd/migration/rust-evidence/m203-s08-c4-full-diagnostics.jsonl",
    "prd/migration/rust-evidence/m203-s09-c4-operational-receipt.json",
]
for rel in pins:
    path = Path(rel)
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing frozen pin: {rel}")
    digest = sha256(path.read_bytes()).hexdigest()
    print(f"frozen {rel} sha256:{digest}")
PY

echo S05_VERIFY_OK
