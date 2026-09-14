#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

run_check() {
  uv run python scripts/m205_s01_matrix.py check "$@"
}

run_check
uv run python scripts/m205_s01_matrix.py compose

# The verifier must reject traversal, absolute, backslash, and symlink paths.
if run_check --input ../outside.yaml >/dev/null 2>&1; then
  echo 'traversal path unexpectedly accepted' >&2
  exit 1
fi
if run_check --input /tmp/m205-matrix.yaml >/dev/null 2>&1; then
  echo 'absolute path unexpectedly accepted' >&2
  exit 1
fi
if run_check --input 'prd\\architecture\\m205-s01-pullenti-matrix.yaml' >/dev/null 2>&1; then
  echo 'backslash path unexpectedly accepted' >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/prd/architecture"
ln -s "$PWD/prd/architecture/m205-s01-pullenti-matrix.yaml" "$tmp/prd/architecture/link.yaml"
if uv run python scripts/m205_s01_matrix.py check --root "$tmp" --input prd/architecture/link.yaml >/dev/null 2>&1; then
  echo 'symlink path unexpectedly accepted' >&2
  exit 1
fi

# No product/vendor module import is permitted in the host verifier.
if grep -Eiq '(^|[[:space:]])(from[[:space:]]+pullenti|import[[:space:]]+pullenti|from[[:space:]]+law_nexus|import[[:space:]]+law_nexus)' scripts/m205_s01_matrix.py; then
  echo 'vendor/product import found in host verifier' >&2
  exit 1
fi

echo S01_T01_NEGATIVE_PATHS_OK
echo S01_T01_MATRIX_OK
echo S01_T01_HUMAN_ADOPTION_PENDING_OK
