#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

run_ok() {
  local label=$1; shift
  if ! "$@"; then
    echo "${label}: expected success" >&2
    exit 1
  fi
}
run_fail() {
  local label=$1; shift
  if "$@" >/dev/null 2>&1; then
    echo "${label}: expected failure" >&2
    exit 1
  fi
}

run_ok valid_check uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input prd/architecture/m205-s02-pre-capture-grammar.yaml

# Red smoke uses a bounded temporary directory inside the repository and never
# changes the verifier's working directory or writes a pin.
tmp=$(mktemp -d "$ROOT/.m205-s02-check.XXXXXX")
trap 'rm -rf -- "$tmp"' EXIT
cp -- prd/architecture/m205-s02-pre-capture-grammar.yaml "$tmp/valid.yaml"
run_ok copied_check uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input "${tmp#"$ROOT/"}/valid.yaml"
run_fail missing_input uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input "${tmp#"$ROOT/"}/missing.yaml"

printf 'schema: wrong\n' > "$tmp/wrong.yaml"
run_fail wrong_schema uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input "${tmp#"$ROOT/"}/wrong.yaml"
printf 'a: 1\na: 2\n' > "$tmp/duplicate.yaml"
run_fail duplicate_key uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input "${tmp#"$ROOT/"}/duplicate.yaml"
printf 'a: &anchor 1\nb: *anchor\n' > "$tmp/alias.yaml"
run_fail alias_input uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input "${tmp#"$ROOT/"}/alias.yaml"
run_fail traversal uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input "../etc/passwd"
ln -s -- "$tmp/valid.yaml" "$tmp/symlink.yaml"
run_fail symlink_input uv run python scripts/m205_s02_grammar.py --root "$ROOT" --input "${tmp#"$ROOT/"}/symlink.yaml"

printf 'S02_T02_ADVERSARIAL_OK\n'
