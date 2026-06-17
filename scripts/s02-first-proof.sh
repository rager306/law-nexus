#!/usr/bin/env bash
#
# scripts/s02-first-proof.sh — M064-S02-T01 First Proof tripwire
#
# PURPOSE: Prove the git-lex SHACL shape GENERATOR emits sh:datatype /
# sh:in / sh:minCount when an ontology carries the right axioms — ISOLATED
# from ontology authoring — BEFORE any acp.ttl edit. This is the MEM541
# "never executed the named fix" trap-catcher: if the generator produced
# empty shapes, strengthening acp.ttl would be pointless.
#
# M064 SHAPE-CONTRACT §9 step 1.
#
# PATH NOTE (why adaptive _ontology/ instead of `--kit rager306/git-lex-kit-law-nexus`):
#   The original plan instructed `git-lex init --kit rager306/git-lex-kit-law-nexus`.
#   That kit is NOT published on GitHub (404), and its publication is BLOCKED by
#   project decisions: D083 ("external publishing" blocked), M060-S01
#   ("law-nexus-kit publishing blocked in S01"), M059-S03 ("does not create a
#   kit repository"). git-lex `init`/`kit-update` require a GitHub fetch with
#   no local fallback, so the static-path shapes (`.lex/ontology/law-nexus/`)
#   cannot be generated without publishing the kit.
#
#   The git-lex generator is the SAME for static (`.lex/ontology/`) and adaptive
#   (`_ontology/`) kits — both flow through `generate_shapes_from_store()`,
#   triggered by `find_kit_ttl()`. The adaptive path (`git-lex sync` →
#   `build_adaptive_shapes()`) reads `_ontology/{name}/{name}.ttl` and writes
#   `_ontology/{name}/{name}-shapes.ttl` with NO kit fetch. We therefore place
#   the law-nexus source ontology (the exact file from
#   `git-lex-kit-law-nexus/ontology/law-nexus/law-nexus.ttl`) under `_ontology/`
#   in a disposable /tmp workspace and run `git-lex sync` to generate the
#   shapes. This produces byte-for-byte the same constraint output the static
#   path would (same generator, same axioms), achieving the T01 direct-proof
#   goal without an outward-facing kit publish.
#
# The four axioms proven present in law-nexus.ttl (and therefore emitted):
#   1. lawNexus:synthetic   rdfs:range xsd:boolean        → sh:datatype xsd:boolean
#   2. lawNexus:proofStatus rdfs:range lawNexus:ProofStatus
#                            (ProofStatus owl:oneOf (...)) → sh:in ( ... )
#   3. lawNexus:observedAt  rdfs:range xsd:dateTime       → sh:datatype xsd:dateTime
#   4. owl:Restriction/owl:minCardinality 1
#        (synthetic on LegalDocument, observedAt on ParserRun) → sh:minCount 1
#
# DONE-WHEN: this script exits 0 (all four constraint kinds present in the
# generated law-nexus shapes; no main-checkout residue).
#
# Disposable: all work happens in a mktemp /tmp workspace that is trap-rm'd
# on exit. Idempotent: re-runnable.
set -euo pipefail

GIT_LEX="${GIT_LEX:-/root/vendor-source/git-lex/target/debug/git-lex}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAW_NEXUS_TTL="$REPO_ROOT/git-lex-kit-law-nexus/ontology/law-nexus/law-nexus.ttl"
MAIN_RESIDUE_NAMES=(.lex Squad Raw .artifacts)

# --- preconditions ---------------------------------------------------------
[ -x "$GIT_LEX" ] || { echo "FATAL: git-lex binary not executable: $GIT_LEX" >&2; exit 1; }
[ -f "$LAW_NEXUS_TTL" ] || { echo "FATAL: law-nexus.ttl not found: $LAW_NEXUS_TTL" >&2; exit 1; }

# --- disposable /tmp workspace --------------------------------------------
WS="$(mktemp -d /tmp/s02-first-proof-XXXXXX)"
cleanup() {
  rm -rf "$WS"
}
trap cleanup EXIT

echo "[T01] workspace: $WS"

# --- baseline residue guard (main checkout must start clean) ----------------
for name in "${MAIN_RESIDUE_NAMES[@]}"; do
  if [ -e "$REPO_ROOT/$name" ]; then
    echo "FATAL: main checkout already has residue '$name' before run — refusing to proceed" >&2
    exit 1
  fi
done

# --- seed an isolated git repo with the law-nexus ontology as adaptive -----
# git-lex resolves the repo root via `git rev-parse --show-toplevel`, so
# operating inside $WS keeps the main checkout untouched.
(
  cd "$WS"
  git init -q
  git config user.email "t01-proof@local"
  git config user.name "t01-proof"

  # Adaptive ontology location: _ontology/{short}/{short}.ttl (fetch-free).
  mkdir -p "$WS/_ontology/law-nexus"
  cp "$LAW_NEXUS_TTL" "$WS/_ontology/law-nexus/law-nexus.ttl"

  # `git-lex sync` regenerates adaptive shapes unconditionally, but requires a
  # non-empty HEAD (`git rev-parse HEAD`). Seed a commit so sync runs.
  git add -A
  git commit -qm "seed law-nexus adaptive ontology"
)

# --- git-lex init (base kit only) — records output to a log in the ws ------
# Installs the .lex scaffold and pre-commit hook. No domain kit is fetched
# (publication blocked), so the static kit path is intentionally unused here.
echo "[T01] git-lex init (base kit) ..."
(
  cd "$WS"
  GIT_TERMINAL_PROMPT=0 "$GIT_LEX" init . >"$WS/init.log" 2>&1
) || { echo "FATAL: git-lex init failed — see $WS/init.log" >&2; cat "$WS/init.log" >&2; exit 1; }

# Commit anything init scaffolded so sync has a fresh HEAD.
(
  cd "$WS"
  git add -A
  git commit -qm "post-init scaffold" >/dev/null 2>&1 || true
)

# --- git-lex sync — generates the adaptive law-nexus shapes (no kit fetch) --
echo "[T01] git-lex sync (builds adaptive law-nexus shapes) ..."
(
  cd "$WS"
  GIT_TERMINAL_PROMPT=0 "$GIT_LEX" sync >"$WS/sync.log" 2>&1
) || { echo "FATAL: git-lex sync failed — see $WS/sync.log" >&2; cat "$WS/sync.log" >&2; exit 1; }

SHAPES="$WS/_ontology/law-nexus/law-nexus-shapes.ttl"
[ -f "$SHAPES" ] || {
  echo "FATAL: generated shapes not found: $SHAPES" >&2
  echo "----- sync.log -----" >&2; cat "$WS/sync.log" >&2
  exit 1
}

echo "[T01] shapes: $SHAPES"

# --- assert the four constraint kinds are emitted --------------------------
# Per the tripwire contract: any missing kind means a deeper generator bug —
# STOP before editing acp.ttl.
fail_kind() {
  local kind="$1" count="$2"
  echo "FAIL: constraint kind '$kind' missing (count=$count) — generator did NOT emit it from law-nexus axioms." >&2
  echo "      This is the MEM541 tripwire: STOP before editing acp.ttl." >&2
  echo "----- generated shapes ($SHAPES) -----" >&2
  cat "$SHAPES" >&2
  exit 1
}

c_bool=$(grep -c 'sh:datatype xsd:boolean' "$SHAPES" || true)
[ "$c_bool" -ge 1 ] || fail_kind "sh:datatype xsd:boolean (lawNexus:synthetic)" "$c_bool"

c_in=$(grep -c 'sh:in (' "$SHAPES" || true)
[ "$c_in" -ge 1 ] || fail_kind "sh:in ( (lawNexus:proofStatus owl:oneOf)" "$c_in"

c_dt=$(grep -c 'sh:datatype xsd:dateTime' "$SHAPES" || true)
[ "$c_dt" -ge 1 ] || fail_kind "sh:datatype xsd:dateTime (lawNexus:observedAt)" "$c_dt"

c_min=$(grep -c 'sh:minCount 1' "$SHAPES" || true)
[ "$c_min" -ge 2 ] || fail_kind "sh:minCount 1 (synthetic on LegalDocument + observedAt on ParserRun; expected >=2)" "$c_min"

# --- assert no main-checkout residue (.lex, Squad, Raw, .artifacts) --------
for name in "${MAIN_RESIDUE_NAMES[@]}"; do
  if [ -e "$REPO_ROOT/$name" ]; then
    echo "FATAL: main-checkout residue detected: $REPO_ROOT/$name" >&2
    exit 1
  fi
done

echo "[T01] PASS — generator emits all 4 constraint kinds from law-nexus axioms:"
echo "        sh:datatype xsd:boolean = $c_bool"
echo "        sh:in (                 = $c_in"
echo "        sh:datatype xsd:dateTime= $c_dt"
echo "        sh:minCount 1           = $c_min"
echo "        main-checkout residue   = clean"
echo "[T01] generator proven pre-acp.ttl (MEM541 trap cleared)."
exit 0
