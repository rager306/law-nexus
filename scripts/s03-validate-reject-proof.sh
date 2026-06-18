#!/usr/bin/env bash
#
# scripts/s03-validate-reject-proof.sh — M064-S03-T02 runtime reject-proof
#
# PURPOSE: Empirically prove the S02-strengthened acp.ttl (v0.2.0) not only
# REACHES the generated SHACL shapes (proven by scripts/s02-self-check.sh)
# but actually makes `git-lex validate` REJECT true-negative records and
# ACCEPT the positive counterpart. This is the MEM541/MEM541-trap catcher
# for the per-class enforcement gate — the single genuinely unproven
# empirical step that S03 owns. S02 proved "constraints reach generation";
# this script proves "constraints reach enforcement / validate rejects".
#
# The proof: in a disposable /tmp workspace seeded with the REAL published
# acp-kit, delete the 3 nonAuthoritative-bearing published examples (they
# spuriously fail the v0.2.0 boolean-datatype overlay per D087), drop in the
# 3 S03 fixtures (1 positive + 2 true-negatives), overlay the strengthened
# acp.ttl as an adaptive ontology, sync to regenerate adaptive shapes, then
# run `git-lex validate` and assert it exits ≠0 naming EXACTLY the 2
# negatives (MinCount + sh:in) and accepting the positive.
#
# DONE-WHEN: this script exits 0 — meaning validate rejected exactly the 2
# negatives with the contracted constraint kinds (sh:minCount on
# EvidenceAnchor, sh:in on ProofGate) and accepted the positive, the
# regenerated shapes carried both constraint kinds, no main-checkout
# residue leaked, and the JSON proof-summary is written to
# prd/architecture/acp/runtime/m064-s03/validate-proof.json.
#
# ---------------------------------------------------------------------------
# ENFORCEMENT MECHANIC (source-verified before authoring):
#   `git-lex validate` (main.rs cmd_validate) concatenates SHACL shapes from
#   BOTH `.lex/ontology/{short}/{short}-shapes.ttl` (kit-owned, v0.1.0) AND
#   `_ontology/{name}/{name}-shapes.ttl` (agent-authored adaptive, regenerated
#   by `git-lex sync` from the strengthened ttl) into one shapes graph, then
#   validates every .md via frontmatter_to_turtle. On ≥1 violation it prints
#   "Validated N files in Xms — M violation(s) in K file(s)" to stderr and the
#   Validate dispatch runs `exit(1)`. So the strengthened adaptive overlay
#   reaches enforcement — the opposite of M061/S04's "pass-with-shape-
#   violation" baseline, which used the v0.1.0 static-only shapes (no
#   constraints → nothing to violate → exit 0 "all pass"). This script closes
#   that gap.
#
# WHY DELETE THE 3 PUBLISHED EXAMPLES (D087): the kit ships
# SourceRecord/example-source-record.md, Decision/example-decision.md, and
# ProofGate/example-proof-gate.md, all carrying `nonAuthoritative: true`.
# Under the v0.2.0 adaptive overlay, enforcement adds sh:datatype xsd:boolean
# to nonAuthoritative, but extraction (frontmatter_to_turtle) reads the
# STATIC v0.1.0 shapes and emits nonAuthoritative as an untyped string, so
# every boolean-bearing record would spuriously fail the datatype constraint
# and pollute the violator set. The S03 fixtures omit nonAuthoritative
# entirely (D087), so deleting the 3 published examples keeps the proof set
# to EXACTLY the 2 intended negatives.
# ---------------------------------------------------------------------------
#
# Disposable: all git-lex work happens in a mktemp /tmp workspace that is
# trap-rm'd on exit. Idempotent: re-runnable. Network required (GitHub kit
# fetch).
set -euo pipefail

GIT_LEX="${GIT_LEX:-/root/vendor-source/git-lex/target/debug/git-lex}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRENGTHENED_ACP_TTL="$REPO_ROOT/git-lex-kit-acp/ontology/acp/acp.ttl"
FIXTURE_EA_POS="$REPO_ROOT/git-lex-kit-acp/content/ACP/EvidenceAnchor/example-evidence-anchor.md"
FIXTURE_EA_NEG="$REPO_ROOT/git-lex-kit-acp/content/ACP/EvidenceAnchor/example-evidence-anchor-missing-source-artifact.md"
FIXTURE_PG_NEG="$REPO_ROOT/git-lex-kit-acp/content/ACP/ProofGate/example-proof-gate-invalid-verdict.md"
ACP_KIT_SPEC="rager306/git-lex-kit-acp"
MAIN_RESIDUE_NAMES=(.lex Squad Raw .artifacts)

# Paths produced by the proof (relative to repo root).
PROOF_DIR="$REPO_ROOT/prd/architecture/acp/runtime/m064-s03"
PROOF_JSON="$PROOF_DIR/validate-proof.json"

# Published boolean-bearing examples that must be removed from the workspace
# (would spuriously fail the v0.2.0 datatype overlay — D087).
PUBLISHED_BOOLEAN_EXAMPLES=(
  "ACP/SourceRecord/example-source-record.md"
  "ACP/Decision/example-decision.md"
  "ACP/ProofGate/example-proof-gate.md"
)

# The relpaths the validate violator block MUST name (negatives) / NOT name
# (positive). These are the S03 fixtures copied into the workspace.
EA_NEG_REL="ACP/EvidenceAnchor/example-evidence-anchor-missing-source-artifact.md"
PG_NEG_REL="ACP/ProofGate/example-proof-gate-invalid-verdict.md"
EA_POS_REL="ACP/EvidenceAnchor/example-evidence-anchor.md"

# --- preconditions ---------------------------------------------------------
[ -x "$GIT_LEX" ] || { echo "FATAL: git-lex binary not executable: $GIT_LEX" >&2; exit 1; }
[ -f "$STRENGTHENED_ACP_TTL" ] || { echo "FATAL: strengthened acp.ttl not found: $STRENGTHENED_ACP_TTL" >&2; exit 1; }
# The strengthened ontology must carry the v0.2.0 constraint set (S02 T02).
grep -q 'owl:versionInfo "0.2.0"' "$STRENGTHENED_ACP_TTL" || {
  echo "FATAL: $STRENGTHENED_ACP_TTL is not the strengthened v0.2.0 ontology (S02 not applied)" >&2
  exit 1
}
for f in "$FIXTURE_EA_POS" "$FIXTURE_EA_NEG" "$FIXTURE_PG_NEG"; do
  [ -f "$f" ] || { echo "FATAL: S03 fixture not found: $f" >&2; exit 1; }
done

# --- disposable /tmp workspace --------------------------------------------
WS="$(mktemp -d /tmp/s03-reject-XXXXXX)"
cleanup() {
  rm -rf "$WS"
}
trap cleanup EXIT

echo "[T02] workspace: $WS"

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
  git config user.email "t02-reject-proof@local"
  git config user.name "t02-reject-proof"
)

# --- git-lex init --kit (REAL published acp-kit, GitHub download) ----------
# Downloads base kit + rager306/git-lex-kit-acp, installs .lex/ scaffold +
# content examples + static shapes (from the published, un-strengthened
# acp.ttl). Output logged in the ws.
echo "[T02] git-lex init --kit $ACP_KIT_SPEC (published kit, GitHub fetch) ..."
(
  cd "$WS"
  GIT_TERMINAL_PROMPT=0 "$GIT_LEX" init --kit "$ACP_KIT_SPEC" "$WS" >"$WS/init.log" 2>&1
) || { echo "FATAL: git-lex init failed — see $WS/init.log" >&2; cat "$WS/init.log" >&2; exit 1; }

# Confirm the domain kit was actually fetched (not just the base kit).
grep -q "Additional kit installed" "$WS/init.log" || {
  echo "FATAL: domain acp-kit did not install — see $WS/init.log" >&2; cat "$WS/init.log" >&2; exit 1
}
echo "[T02] acp-kit downloaded + static shapes generated (published v0.1.0 acp.ttl)."

# --- delete the 3 published boolean-bearing examples (D087 cleanup) --------
# These carry nonAuthoritative:true and would spuriously fail the v0.2.0
# boolean-datatype overlay, polluting the violator set beyond the 2 intended
# negatives. Removing them keeps the proof set EXACTLY 2 negatives + 1 positive.
echo "[T02] deleting 3 published nonAuthoritative-bearing examples (D087) ..."
for rel in "${PUBLISHED_BOOLEAN_EXAMPLES[@]}"; do
  if [ -f "$WS/$rel" ]; then
    rm -f "$WS/$rel"
    echo "        removed $rel"
  fi
done

# --- copy the 3 S03 fixtures into the workspace content tree ---------------
echo "[T02] copying 3 S03 fixtures (1 positive + 2 true-negatives) ..."
cp "$FIXTURE_EA_POS" "$WS/ACP/EvidenceAnchor/"
cp "$FIXTURE_EA_NEG" "$WS/ACP/EvidenceAnchor/"
cp "$FIXTURE_PG_NEG" "$WS/ACP/ProofGate/"
echo "        + $EA_POS_REL (positive)"
echo "        + $EA_NEG_REL (negative, sh:minCount)"
echo "        + $PG_NEG_REL (negative, sh:in)"

# --- overlay the strengthened acp.ttl as an ADAPTIVE ontology --------------
# _ontology/{short}/{short}.ttl is agent-owned: git-lex NEVER force-clobbers
# it (kit.rs seeds adaptive ontologies with skip-existing). `git-lex sync`
# reads it via build_adaptive_shapes and writes _ontology/acp/acp-shapes.ttl,
# and `git-lex validate` merges adaptive shapes into the enforcement graph.
mkdir -p "$WS/_ontology/acp"
cp "$STRENGTHENED_ACP_TTL" "$WS/_ontology/acp/acp.ttl"
echo "[T02] overlayed strengthened acp.ttl as adaptive ontology (_ontology/acp/)."

# --- seed HEAD so `git-lex sync` will run build_adaptive_shapes -------------
# git-lex init installs a pre-commit hook that runs extract+validate, but the
# hook cannot find the git-lex binary on PATH here, so init's auto-commit
# silently leaves HEAD empty. `git-lex sync` returns early ("No commits yet")
# when HEAD is empty, before build_adaptive_shapes. Bypass the hook with
# --no-verify to establish HEAD purely for the sync shape-regeneration trigger.
(
  cd "$WS"
  git add -A
  git commit --no-verify -qm "seed fixtures + adaptive acp ontology" >/dev/null 2>&1 || true
)
[ -n "$(git -C "$WS" rev-parse HEAD 2>/dev/null || true)" ] || {
  echo "FATAL: could not establish HEAD in $WS (sync needs it)" >&2; exit 1
}

# --- git-lex sync — regenerate adaptive shapes from the strengthened ttl ----
echo "[T02] git-lex sync (regenerate adaptive acp-shapes.ttl from strengthened ttl) ..."
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
echo "[T02] shapes regenerated: $SHAPES"

# --- assert the regenerated shapes carry BOTH contracted constraint kinds ---
# The proof requires the negative fixtures to be trippable, so the shapes
# MUST carry sh:minCount 1 (EvidenceAnchor.sourceArtifact) and sh:in ( (
# ProofGate.verdict). This re-confirms S02's reach-generation result on the
# exact shapes the validate step below will enforce.
fail_kind() {
  local kind="$1" detail="$2"
  echo "FAIL: constraint kind '$kind' ($detail) missing in regenerated shapes." >&2
  echo "      validate cannot reject the contracted negatives without it." >&2
  echo "----- regenerated shapes ($SHAPES) -----" >&2
  cat "$SHAPES" >&2
  exit 1
}
c_min=$(grep -c 'sh:minCount 1' "$SHAPES" || true)
[ "$c_min" -ge 2 ] || fail_kind "sh:minCount 1" "sourceArtifact→EvidenceAnchor + verdict→ProofGate (expected >=2)"
c_in=$(grep -c 'sh:in (' "$SHAPES" || true)
[ "$c_in" -ge 1 ] || fail_kind "sh:in (" "verdict→ProofGate (expected >=1)"
echo "[T02] shapes carry sh:minCount 1 (=$c_min) and sh:in ( (=$c_in)."

# --- git-lex validate — capture rc + stderr WITHOUT letting set -e abort ----
# This is the heart of the proof. validate is EXPECTED to exit ≠0 here (it
# must reject the 2 negatives). We must capture that non-zero rc rather than
# let `set -e` abort the script before the assertions run.
echo "[T02] git-lex validate (expecting reject: 2 negatives) ..."
validate_log="$WS/validate.log"
validate_rc=0
(
  cd "$WS"
  GIT_TERMINAL_PROMPT=0 "$GIT_LEX" validate >"$validate_log" 2>&1
) || validate_rc=$?
echo "[T02] validate exit code = $validate_rc"

VAL_ERR="$(cat "$validate_log")"
# The summary line git-lex prints on violations:
#   "Validated N files in Xms — M violation(s) in K file(s)"
SUMMARY_LINE="$(grep -E 'violation\(s\) in [0-9]+ file\(s\)' "$validate_log" || true)"

# --- THE PROOF ASSERTIONS --------------------------------------------------
fail_proof() {
  local msg="$1"
  echo "FAIL: $msg" >&2
  echo "----- validate.log -----" >&2
  cat "$validate_log" >&2
  echo "----- regenerated shapes ($SHAPES) -----" >&2
  cat "$SHAPES" >&2
  exit 1
}

# (a) validate MUST exit non-zero (reject path engaged).
[ "$validate_rc" -ne 0 ] || fail_proof "validate exited 0 — the 2 negatives were NOT rejected (enforcement did not engage)."

# (b) stderr MUST contain the summary line naming exactly 2 violator files.
[ -n "$SUMMARY_LINE" ] || fail_proof "validate summary line 'violation(s) in N file(s)' not found in stderr."
echo "$SUMMARY_LINE" | grep -qE '2 violation\(s\) in 2 file\(s\)' \
  || fail_proof "validate did not report exactly 2 violators — expected '2 violation(s) in 2 file(s)', got: $SUMMARY_LINE"

# (c) EA-negative MUST be named with a MinCount constraint.
echo "$VAL_ERR" | grep -F "$EA_NEG_REL" > /dev/null \
  || fail_proof "EA-negative relpath not named in violation block: $EA_NEG_REL"
echo "$VAL_ERR" | grep -qi 'MinCount' \
  || fail_proof "EA-negative did not trip a MinCount constraint (no 'MinCount' in violation block)."

# (d) PG-negative MUST be named with an sh:in / In constraint.
echo "$VAL_ERR" | grep -F "$PG_NEG_REL" > /dev/null \
  || fail_proof "PG-negative relpath not named in violation block: $PG_NEG_REL"
# The shacl_validation library emits "In constraint not satisfied. Expected one of:".
echo "$VAL_ERR" | grep -qiE 'In constraint|sh:in|one of' \
  || fail_proof "PG-negative did not trip an sh:in / In constraint (no 'In constraint'/'sh:in'/'one of' in violation block)."

# (e) the positive MUST NOT appear in the violation block (it passes).
if echo "$VAL_ERR" | grep -F "$EA_POS_REL" > /dev/null 2>&1; then
  fail_proof "positive relpath appeared in violation block (should have passed): $EA_POS_REL"
fi

echo "[T02] PASS — validate rejects exactly the 2 negatives, accepts the positive:"
echo "        $SUMMARY_LINE"
echo "        $EA_NEG_REL → MinCount"
echo "        $PG_NEG_REL → sh:in (In constraint)"
echo "        $EA_POS_REL → accepted (not in violation block)"

# --- write the durable JSON proof-summary ---------------------------------
# Create the runtime dir (with a .gitkeep) so the dir is committed even if
# the JSON is later removed; the JSON lets a cold-start S04 agent read the
# before/after contrast against M061/S04's pass-with-shape-violation baseline
# without re-running the proof.
mkdir -p "$PROOF_DIR"
[ -f "$PROOF_DIR/.gitkeep" ] || : > "$PROOF_DIR/.gitkeep"

# git-lex exposes no --version / version subcommand; record the binary path +
# mtime as the version surrogate, marked null where unobtainable.
BIN_MTIME="$(stat -c '%y' "$GIT_LEX" 2>/dev/null | cut -d'.' -f1 || echo 'unknown')"

python3 - "$PROOF_JSON" "$GIT_LEX" "$BIN_MTIME" "$validate_rc" "$SUMMARY_LINE" "$EA_NEG_REL" "$PG_NEG_REL" "$EA_POS_REL" <<'PY'
import json, sys, datetime
out, bin_path, bin_mtime, vrc, summary, ea_neg, pg_neg, ea_pos = sys.argv[1:9]
proof = {
    "schema_version": "m064-s03-validate-proof/v1",
    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "purpose": "M064-S03-T02 runtime reject-proof: git-lex validate exits !=0 on exactly the 2 true-negative fixtures (EvidenceAnchor sh:minCount, ProofGate sh:in) and accepts the positive EvidenceAnchor fixture, after S02-strengthened acp.ttl v0.2.0 reaches enforcement via the adaptive overlay.",
    "git_lex": {
        "binary": bin_path,
        "version": None,
        "binary_mtime": bin_mtime,
        "version_note": "git-lex exposes no --version flag or version subcommand; binary path + mtime are the version surrogate."
    },
    "kit_spec": "rager306/git-lex-kit-acp",
    "ontology_version": "0.2.0",
    "overlay_mechanic": "adaptive ontology at _ontology/acp/acp.ttl; git-lex sync regenerates _ontology/acp/acp-shapes.ttl; git-lex validate merges adaptive shapes into the enforcement graph (main.rs cmd_validate).",
    "validate_exit_code": int(vrc),
    "validate_expected_exit_code": "non-zero (reject path)",
    "summary_line": summary,
    "fixtures": {
        "positive": {
            "relpath": ea_pos,
            "verdict": "pass",
            "note": "carries acp.EvidenceAnchor.sourceArtifact; not present in the violation block."
        },
        "ea_negative": {
            "relpath": ea_neg,
            "verdict": "reject-MinCount",
            "constraint": "sh:minCount 1 on EvidenceAnchor.sourceArtifact",
            "violation_message_marker": "MinCount(1) not satisfied"
        },
        "pg_negative": {
            "relpath": pg_neg,
            "verdict": "reject-sh:in",
            "constraint": "sh:in on ProofGate.verdict (VerdictValue enum)",
            "violation_message_marker": "In constraint not satisfied. Expected one of:"
        }
    },
    "baseline_contrast": "M061/S04 diagnostics.jsonl showed git-lex validate exit 0 ('all pass') with 'pass-with-shape-violation' classification under the v0.1.0 static-only shapes (no constraints to violate). This proof shows the strengthened v0.2.0 adaptive overlay closes that gap: validate now exits 1 naming the 2 negatives."
}
with open(out, "w") as f:
    json.dump(proof, f, indent=2)
    f.write("\n")
print("[T02] wrote", out)
PY

# --- post-run residue guard (main checkout must remain clean) --------------
for name in "${MAIN_RESIDUE_NAMES[@]}"; do
  if [ -e "$REPO_ROOT/$name" ]; then
    echo "FATAL: main-checkout residue detected after run: $REPO_ROOT/$name" >&2
    exit 1
  fi
done

echo "[T02] main-checkout residue = clean"
echo "[T02] DONE: validate-reject proof holds — S03 enforcement gate cleared."
exit 0
