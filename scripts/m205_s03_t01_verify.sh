#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
VERIFIER=(uv run python scripts/m205_s03_fsm.py --root "$ROOT")

run_ok() {
  local label=$1
  shift
  if ! "$@"; then
    echo "${label}: expected success" >&2
    exit 1
  fi
}

run_fail() {
  local label=$1
  shift
  if "$@" >/dev/null 2>&1; then
    echo "${label}: expected failure" >&2
    exit 1
  fi
}

run_ok valid_check "${VERIFIER[@]}" --input prd/architecture/m205-s03-context-fsm.yaml

tmp=$(mktemp -d "$ROOT/.m205-s03-check.XXXXXX")
trap 'rm -rf -- "$tmp"' EXIT
rel_tmp=${tmp#"$ROOT/"}

cp -- prd/architecture/m205-s03-context-fsm.yaml "$tmp/valid.yaml"
run_ok copied_check "${VERIFIER[@]}" --input "$rel_tmp/valid.yaml"
run_fail missing_input "${VERIFIER[@]}" --input "$rel_tmp/missing.yaml"
printf 'schema: wrong\n' > "$tmp/wrong.yaml"
run_fail wrong_schema "${VERIFIER[@]}" --input "$rel_tmp/wrong.yaml"
printf 'a: 1\na: 2\n' > "$tmp/duplicate.yaml"
run_fail duplicate_key "${VERIFIER[@]}" --input "$rel_tmp/duplicate.yaml"
printf 'a: &anchor 1\nb: *anchor\n' > "$tmp/alias.yaml"
run_fail alias_input "${VERIFIER[@]}" --input "$rel_tmp/alias.yaml"
run_fail traversal "${VERIFIER[@]}" --input '../etc/passwd'
ln -s -- "$tmp/valid.yaml" "$tmp/symlink.yaml"
run_fail symlink_input "${VERIFIER[@]}" --input "$rel_tmp/symlink.yaml"
uv run python - "$tmp/oversize.yaml" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).write_bytes(b"x" * (64 * 1024 + 1))
PY
run_fail byte_cap "${VERIFIER[@]}" --input "$rel_tmp/oversize.yaml"

printf 'S03_T01_FSM_OK\n'
printf 'S03_T01_BOUNDARIES_OK\n'
