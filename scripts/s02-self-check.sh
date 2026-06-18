#!/usr/bin/env bash
#
# scripts/s02-self-check.sh — M064-S02-T04 self-check
#
# PURPOSE: Empirically prove the strengthened acp.ttl (v0.2.0, T02) actually
# reaches the GENERATED SHACL shapes — the MEM541 "never executed the named fix"
# trap-catcher for the ACP-kit. Without this proof, S02 would "implement
# constraints" that might still produce empty shapes (MEM539 showed the v0.1.0
# shapes attach NO datatype/enum/minCount constraints to class shapes).
# This is M064 SHAPE-CONTRACT §9 step 6.
#
# DONE-WHEN: this script exits 0 — the strengthened ttl generates the 3
# contracted constraint kinds (sh:datatype xsd:boolean on nonAuthoritative,
# sh:in on verdict, sh:minCount 1 on verdict→ProofGate + sourceArtifact→
# EvidenceAnchor), the 3 committed ACP examples still validate ("all pass"),
# and no main-checkout residue is produced.
#
# ---------------------------------------------------------------------------
# MECHANIC NOTE (deviation from the literal plan command — documented, as T01
# documented its own path adaptation):
#
# The plan instructed: init the published acp-kit, overlay the strengthened
# acp.ttl onto EVERY acp.ttl copy under <ws>, then `git-lex kit-update` to
# regenerate the STATIC shapes. That literal sequence is EMPIRICALLY BROKEN:
# `git-lex init` and `git-lex kit-update` ALWAYS clobber the static kit
# ontology (`.lex/ontology/{short}/{short}.ttl`) from the freshly-fetched
# GitHub tarball — kit.rs install_scaffold_files_from_skip_existing calls
# install_recursive(ontology_src, ontology_dest, force=true) unconditionally
# for static kits ("ontology ALWAYS overwritten — kit's schema, must stay in
# sync"). So kit-update reverts the overlaid acp.ttl back to the published
# v0.1.0 BEFORE regenerating, and the regenerated static shapes carry zero
# constraints (verified: clobber + 0/0/0 counts). `git-lex sync` only
# regenerates ADAPTIVE shapes (_ontology/*-shapes.ttl), never static.
#
# Working pattern (proven empirically in /tmp before authoring this script):
# the git-lex SHACL GENERATOR (shacl.rs generate_shapes_from_store) is the
# SAME code path for static (`.lex/ontology/`) and adaptive (`_ontology/`)
# kits — confirmed by S01 source read, the T01 first-proof, and F5. So we:
#   1. Run the REAL published kit via `init --kit rager306/git-lex-kit-acp`
#      (proves the GitHub download works and the 3 committed examples
#      validate against the kit shapes — the "Validated N files — all pass"
#      line).
#   2. Seed the strengthened acp.ttl as an ADAPTIVE ontology at
#      `_ontology/acp/acp.ttl` (agent-owned, NEVER force-clobbered) and run
#      `git-lex sync`, which calls build_adaptive_shapes → generates
#      `_ontology/acp/acp-shapes.ttl` carrying the strengthened constraints.
# This proves the exact DONE-WHEN claim (the strengthened ttl generates the
# 3 constraint kinds) while still exercising the real published kit. The
# per-class true-negative REJECT proof (validate rejects bad records) is
# S03's gate — S02 only proves the constraint kinds reach generation.
# ---------------------------------------------------------------------------
#
# Disposable: all git-lex work happens in a mktemp /tmp workspace that is
# trap-rm'd on exit. Idempotent: re-runnable. Network required (GitHub kit
# fetch).
set -euo pipefail

GIT_LEX="${GIT_LEX:-/root/vendor-source/git-lex/target/debug/git-lex}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRENGTHENED_ACP_TTL="$REPO_ROOT/git-lex-kit-acp/ontology/acp/acp.ttl"
ACP_KIT_SPEC="rager306/git-lex-kit-acp"
MAIN_RESIDUE_NAMES=(.lex Squad Raw .artifacts)

# --- preconditions ---------------------------------------------------------
[ -x "$GIT_LEX" ] || { echo "FATAL: git-lex binary not executable: $GIT_LEX" >&2; exit 1; }
[ -f "$STRENGTHENED_ACP_TTL" ] || { echo "FATAL: strengthened acp.ttl not found: $STRENGTHENED_ACP_TTL" >&2; exit 1; }
# The strengthened ontology must carry the v0.2.0 constraint set (T02).
grep -q 'owl:versionInfo "0.2.0"' "$STRENGTHENED_ACP_TTL" || {
  echo "FATAL: $STRENGTHENED_ACP_TTL is not the strengthened v0.2.0 ontology (T02 not applied)" >&2
  exit 1
}

# --- disposable /tmp workspace --------------------------------------------
WS="$(mktemp -d /tmp/s02-self-check-XXXXXX)"
cleanup() {
  rm -rf "$WS"
}
trap cleanup EXIT

echo "[T04] workspace: $WS"

# --- baseline residue guard (main checkout must start clean) ----------------
for name in "${MAIN_RESIDUE_NAMES[@]}"; do
  if [ -e "$REPO_ROOT/$name" ]; then
    echo "FATAL: main checkout already has residue '$name' before run — refusing to proceed" >&2
    exit 1
  fi
done

# --- seed an isolated git repo --------------------------------------------
# git-lex resolves the repo root via `git rev-parse --show-toplevel`, so
# operating inside $WS keeps the main checkout untouched.
(
  cd "$WS"
  git init -q
  git config user.email "t04-self-check@local"
  git config user.name "t04-self-check"
)

# --- git-lex init --kit (REAL published acp-kit, GitHub download) ----------
# Downloads base kit + rager306/git-lex-kit-acp, installs .lex/ scaffold +
# content examples + static shapes (from the published, un-strengthened
# acp.ttl). Output logged in the ws.
echo "[T04] git-lex init --kit $ACP_KIT_SPEC (published kit, GitHub fetch) ..."
(
  cd "$WS"
  GIT_TERMINAL_PROMPT=0 "$GIT_LEX" init --kit "$ACP_KIT_SPEC" "$WS" >"$WS/init.log" 2>&1
) || { echo "FATAL: git-lex init failed — see $WS/init.log" >&2; cat "$WS/init.log" >&2; exit 1; }

# Confirm the domain kit was actually fetched (not just the base kit).
grep -q "Additional kit installed" "$WS/init.log" || {
  echo "FATAL: domain acp-kit did not install — see $WS/init.log" >&2; cat "$WS/init.log" >&2; exit 1
}
echo "[T04] acp-kit downloaded + static shapes generated (published v0.1.0 acp.ttl)."

# --- git-lex validate — the 3 committed ACP examples -----------------------
# The kit ships 3 example records (content/ACP/{Decision,ProofGate,SourceRecord}).
# validate loads the kit shapes and checks every document. The done-when line
# is "Validated N files ... all pass".
echo "[T04] git-lex validate (3 committed ACP examples) ..."
(
  cd "$WS"
  GIT_TERMINAL_PROMPT=0 "$GIT_LEX" validate >"$WS/validate.log" 2>&1
) || { echo "FATAL: git-lex validate failed — see $WS/validate.log" >&2; cat "$WS/validate.log" >&2; exit 1; }

if ! grep -Eq 'Validated [0-9]+ files .*all pass' "$WS/validate.log"; then
  echo "FAIL: validate did not report the 'all pass' line — see $WS/validate.log" >&2
  cat "$WS/validate.log" >&2
  exit 1
fi
VAL_LINE="$(grep -E 'Validated [0-9]+ files' "$WS/validate.log")"
echo "[T04] $VAL_LINE"

# --- seed HEAD so `git-lex sync` will run build_adaptive_shapes -------------
# git-lex init installs a pre-commit hook that runs extract+validate, but the
# hook cannot find the git-lex binary on PATH here, so init's auto-commit
# silently leaves HEAD empty. `git-lex sync` returns early ("No commits yet")
# when HEAD is empty, before build_adaptive_shapes. Bypass the hook with
# --no-verify to establish HEAD purely for the sync shape-regeneration trigger.
(
  cd "$WS"
  git add -A
  git commit --no-verify -qm "seed post-init scaffold" >/dev/null 2>&1 || true
)
[ -n "$(git -C "$WS" rev-parse HEAD 2>/dev/null || true)" ] || {
  echo "FATAL: could not establish HEAD in $WS (sync needs it)" >&2; exit 1
}

# --- overlay the strengthened acp.ttl as an ADAPTIVE ontology --------------
# _ontology/{short}/{short}.ttl is agent-owned: git-lex NEVER force-clobbers
# it (kit.rs seeds adaptive ontologies with skip-existing). `git-lex sync`
# reads it via build_adaptive_shapes and writes _ontology/acp/acp-shapes.ttl.
# This routes the strengthened ontology through the SAME generator the static
# path uses (shacl.rs generate_shapes_from_store), proving the axioms reach
# generated shapes — the MEM541 proof.
echo "[T04] overlay strengthened acp.ttl as adaptive ontology (_ontology/acp/) ..."
mkdir -p "$WS/_ontology/acp"
cp "$STRENGTHENED_ACP_TTL" "$WS/_ontology/acp/acp.ttl"
(
  cd "$WS"
  git add -A
  git commit --no-verify -qm "overlay strengthened adaptive acp ontology" >/dev/null 2>&1 || true
)

# --- git-lex sync — regenerate adaptive shapes from the strengthened ttl ----
echo "[T04] git-lex sync (regenerate adaptive acp-shapes.ttl from strengthened ttl) ..."
(
  cd "$WS"
  GIT_TERMINAL_PROMPT=0 "$GIT_LEX" sync >"$WS/sync.log" 2>&1
) || { echo "FATAL: git-lex sync failed — see $WS/sync.log" >&2; cat "$WS/sync.log" >&2; exit 1; }

SHAPES="$WS/_ontology/acp/acp-shapes.ttl"
[ -f "$SHAPES" ] || {
  echo "FATAL: regenerated adaptive shapes not found: $SHAPES" >&2
  echo "----- sync.log -----" >&2; cat "$WS/sync.log" >&2
  exit 1
}
echo "[T04] shapes regenerated: $SHAPES"

# --- assert the 3 contracted constraint kinds reach the generated shapes ----
# Per the tripwire contract: a missing kind means the strengthened axioms did
# NOT reach generation — STOP (MEM541 trap). Each kind is also bound to its
# contracted class/property to catch a degenerate emission.
fail_kind() {
  local kind="$1" detail="$2"
  echo "FAIL: constraint kind '$kind' ($detail) missing in regenerated shapes." >&2
  echo "      The strengthened acp.ttl did NOT reach generation — MEM541 trap." >&2
  echo "----- regenerated shapes ($SHAPES) -----" >&2
  cat "$SHAPES" >&2
  exit 1
}

# Kind 1: sh:datatype xsd:boolean on nonAuthoritative.
c_bool=$(grep -c 'sh:datatype xsd:boolean' "$SHAPES" || true)
[ "$c_bool" -ge 1 ] || fail_kind "sh:datatype xsd:boolean" "nonAuthoritative"

# Kind 2: sh:in ( on verdict.
c_in=$(grep -c 'sh:in (' "$SHAPES" || true)
[ "$c_in" -ge 1 ] || fail_kind "sh:in (" "verdict"

# Kind 3a: sh:minCount 1 on verdict (ProofGate shape).
# Kind 3b: sh:minCount 1 on sourceArtifact (EvidenceAnchor shape).
c_min=$(grep -c 'sh:minCount 1' "$SHAPES" || true)
[ "$c_min" -ge 2 ] || fail_kind "sh:minCount 1" "verdict→ProofGate + sourceArtifact→EvidenceAnchor (expected >=2)"

# --- class/property binding guards (degenerate-emission catchers) ----------
# nonAuthoritative must carry the boolean datatype somewhere.
awk '
  /sh:path acp:nonAuthoritative/ { in_na=1 }
  in_na && /sh:datatype xsd:boolean/ { na_ok=1; in_na=0 }
  END { exit na_ok ? 0 : 1 }
' "$SHAPES" || fail_kind "sh:datatype xsd:boolean" "nonAuthoritative binding"

# verdict must carry an sh:in list.
awk '
  /sh:path acp:verdict/ { in_v=1 }
  in_v && /sh:in \(/ { v_ok=1; in_v=0 }
  END { exit v_ok ? 0 : 1 }
' "$SHAPES" || fail_kind "sh:in (" "verdict binding"

# verdict must carry sh:minCount 1 within the ProofGate shape.
awk '
  /sh:targetClass acp:ProofGate/ { in_pg=1 }
  in_pg && /^}/ { in_pg=0 }
  in_pg && /sh:path acp:verdict/ { v=1 }
  in_pg && v && /sh:minCount 1/ { print "ok"; exit }
' "$SHAPES" | grep -q ok || fail_kind "sh:minCount 1" "verdict→ProofGate binding"

# sourceArtifact must carry sh:minCount 1 within the EvidenceAnchor shape.
awk '
  /sh:TargetClass acp:EvidenceAnchor|sh:targetClass acp:EvidenceAnchor/ { in_ea=1 }
  in_ea && /^}/ { in_ea=0 }
  in_ea && /sh:path acp:sourceArtifact/ { sa=1 }
  in_ea && sa && /sh:minCount 1/ { print "ok"; exit }
' "$SHAPES" | grep -q ok || fail_kind "sh:minCount 1" "sourceArtifact→EvidenceAnchor binding"

# --- assert no main-checkout residue (.lex, Squad, Raw, .artifacts) --------
for name in "${MAIN_RESIDUE_NAMES[@]}"; do
  if [ -e "$REPO_ROOT/$name" ]; then
    echo "FATAL: main-checkout residue detected: $REPO_ROOT/$name" >&2
    exit 1
  fi
done

echo "[T04] PASS — strengthened acp.ttl reaches generated shapes:"
echo "        sh:datatype xsd:boolean (nonAuthoritative) = $c_bool"
echo "        sh:in ( (verdict)                          = $c_in"
echo "        sh:minCount 1 (verdict+sourceArtifact)     = $c_min"
echo "        $VAL_LINE"
echo "        main-checkout residue                      = clean"
echo "[T04] MEM541 trap cleared: S02 constraints reach generation (per-class REJECT is S03)."
exit 0
