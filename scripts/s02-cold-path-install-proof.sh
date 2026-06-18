#!/usr/bin/env bash
#
# scripts/s02-cold-path-install-proof.sh
#
# M065-pqvr1r / S02 / T02 — Stage-2 cold-PATH install proof for git-lex.
#
# Proves (all from /tmp, under an EXPLICIT cold PATH that contains ~/.cargo/bin
# and standard system dirs but NO vendor-dir):
#   - the release-installed `git-lex` binary resolves through cold PATH and
#     prints its banner (`git-lex --help` -> rc 0);
#   - the release-installed `git-lex-serve` binary resolves through cold PATH
#     and prints its banner (`git-lex-serve --help` -> rc 0)  [S01 contract §5 item 3];
#   - the git `lex` subcommand dispatches to the installed `git-lex` binary via
#     cold-PATH lookup  [S01 contract §5 item 4];
#   - the --version gap holds: `git lex --version` and `git-lex-serve --version`
#     exit 2 (NO version number is parsed or asserted — hard contract constraint
#     per S01 §5 and M051/S09);
#   - the main law-nexus checkout has no R047 residue (.lex/Squad/Raw/.artifacts)
#     before AND after the proof run.
#
# EMPIRICAL NOTE on `git lex --help`: git intercepts `--help` for EXTERNAL
# subcommands and routes it to man(1) rather than passing the flag to the
# external binary. With no man page installed, `git lex --help` prints
# "No manual entry for git-lex" and exits non-zero (observed rc=16). This is
# git's documented external-subcommand help-dispatch behavior, NOT an install
# defect, and it itself proves git recognizes `lex` as a dispatchable subcommand
# (a non-existent subcommand yields rc=1 "is not a git command"). The cold-PATH
# resolution + dispatch INTENT of contract §5 items 2+4 is therefore proven via
# `git-lex --help` (direct resolution, rc 0 + banner), `git lex` no-args
# dispatch (rc 2 + banner — git found and executed the installed git-lex), and
# `git lex --version` (rc 2, clap error referencing git-lex). The observed
# `git lex --help` behavior is recorded faithfully but is NOT a pass/fail gate.
#
# Output: prd/architecture/acp/runtime/m065-s02/install-proof.json
# (repository-relative tracked evidence anchor).
#
# Idempotent + re-runnable. Fails loud (exit != 0) on any real proof failure or
# R047 residue. Does NOT initialize .lex, does NOT run any mutating git-lex
# surface, does NOT expose serve/viz/listen — CLI-install-only boundary.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT="/root/law-nexus"
PROOF_DIR="$REPO_ROOT/prd/architecture/acp/runtime/m065-s02"
PROOF_JSON="$PROOF_DIR/install-proof.json"

# Explicit cold PATH: ~/.cargo/bin (install target) + standard system dirs.
# Deliberately EXCLUDES /root/vendor-source/git-lex, .../target/debug, and any
# other source/target path so resolution can only come from the install target.
COLD_PATH="/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
# Run every cold invocation from /tmp — a directory OUTSIDE the vendor checkout
# and outside the main law-nexus checkout.
COLD_CWD="/tmp"

BANNER_GIT_LEX="Git extensions for knowledge graphs"
BANNER_GIT_LEX_SERVE="Servers for git-lex knowledge graphs"

# R047 contract-phase residue names that must stay absent in the main checkout.
RESIDUE_NAMES=(".lex" "Squad" "Raw" ".artifacts")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log()  { printf '[s02-proof] %s\n' "$*" >&2; }
fail() { printf '[s02-proof] FATAL: %s\n' "$*" >&2; exit 1; }

# Assert the cold PATH is well-formed (cargo bin present, no vendor leakage).
verify_cold_path() {
  case "$COLD_PATH" in
    *"/root/vendor-source/git-lex"*) fail "COLD_PATH contains the git-lex vendor checkout" ;;
  esac
  case "$COLD_PATH" in
    *"vendor-source"*) fail "COLD_PATH contains a vendor-source path" ;;
  esac
  case "$COLD_PATH" in
    *"target/debug"*) fail "COLD_PATH contains a target/debug path" ;;
  esac
  case "$COLD_PATH" in
    *"/root/.cargo/bin"*) : ;;  # OK
    *) fail "COLD_PATH must contain /root/.cargo/bin" ;;
  esac
  log "cold PATH verified: cargo bin present, no vendor-dir leakage"
}

# Print "absent" or "present:<path>" for one residue name under REPO_ROOT.
residue_state() {
  local name="$1"
  if [[ -e "$REPO_ROOT/$name" ]]; then
    printf 'present'
  else
    printf 'absent'
  fi
}

# Residue guard. $1 = label ("before" | "after"). Exits 1 if any residue present.
guard_residue() {
  local label="$1"
  local rc=0
  for name in "${RESIDUE_NAMES[@]}"; do
    if [[ -e "$REPO_ROOT/$name" ]]; then
      log "residue PRESENT ($label): $name"
      rc=1
    fi
  done
  if [[ $rc -ne 0 ]]; then
    fail "R047 residue guard ($label) failed: residue present in main checkout"
  fi
  log "residue guard ($label): all four names absent (R047 honored)"
}

# Run a command under the cold environment from COLD_CWD.
#   run_cold OUT_VAR RC_VAR -- <command...>
# Captures combined stdout+stderr into OUT_VAR and the real exit code into RC_VAR.
# (Works with `set -e`: the `|| rc=$?` makes the command a conditional.)
run_cold() {
  local out_var="$1"; shift
  local rc_var="$1"; shift
  [[ "${1:-}" == "--" ]] || fail "run_cold: expected '--' separator before command"
  shift
  local rc=0
  local out
  out=$(cd "$COLD_CWD" && env -i HOME=/root PATH="$COLD_PATH" "$@" 2>&1) || rc=$?
  printf -v "$out_var" '%s' "$out"
  printf -v "$rc_var" '%s' "$rc"
}

# Print "true" if $1 contains $2, else "false".
contains() {
  local haystack="$1" needle="$2"
  if [[ "$haystack" == *"$needle"* ]]; then printf 'true'; else printf 'false'; fi
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

log "repo root: $REPO_ROOT"
log "proof json: $PROOF_JSON"
verify_cold_path
mkdir -p "$PROOF_DIR"

# ---------------------------------------------------------------------------
# Baseline residue guard (BEFORE)
# ---------------------------------------------------------------------------

guard_residue "before"

before_dotlex=$(residue_state ".lex")
before_squad=$(residue_state "Squad")
before_raw=$(residue_state "Raw")
before_artifacts=$(residue_state ".artifacts")

# ---------------------------------------------------------------------------
# Cold-PATH proofs (all from /tmp under env -i cold env)
# ---------------------------------------------------------------------------

# Path resolution — proves WHICH binary the cold PATH resolves.
# `command -v` is a shell builtin, so run it through a bash process under the
# cold env (bash is resolved on the cold PATH) instead of passing the builtin
# name directly to env(1).
run_cold glx_cv_out glx_cv_rc -- bash -c 'command -v git-lex'
glx_cv_out="${glx_cv_out%$'\n'}"   # trim trailing newline

run_cold glxs_cv_out glxs_cv_rc -- bash -c 'command -v git-lex-serve'
glxs_cv_out="${glxs_cv_out%$'\n'}"

# (a/b) direct binary resolution through cold PATH
run_cold glx_help_out glx_help_rc -- git-lex --help
glx_help_found=$(contains "$glx_help_out" "$BANNER_GIT_LEX")

# (c) git-lex-serve direct resolution through cold PATH (contract §5 item 3)
run_cold glxs_help_out glxs_help_rc -- git-lex-serve --help
glxs_help_found=$(contains "$glxs_help_out" "$BANNER_GIT_LEX_SERVE")

# git lex --help — recorded faithfully; git intercepts --help -> man(1). NOT a gate.
run_cold glx_dispatch_help_out glx_dispatch_help_rc -- git lex --help

# git lex (no args) — the PRIMARY dispatch proof: git dispatches to git-lex, which
# (clap, no required subcommand) prints the banner + usage and exits 2.
run_cold glx_noargs_out glx_noargs_rc -- git lex
glx_noargs_found=$(contains "$glx_noargs_out" "$BANNER_GIT_LEX")

# Secondary dispatch corroboration: --version is rejected by the dispatched
# git-lex binary (clap error references git-lex). Also the version-gap proof.
run_cold glx_ver_out glx_ver_rc -- git lex --version

# Contrast: a non-existent subcommand yields rc=1 "is not a git command",
# proving git distinguishes a resolved subcommand (lex) from an unknown one.
run_cold contrast_out contrast_rc -- git __nosuchcmd_xyz__ --help

# git-lex-serve --version version gap.
run_cold glxs_ver_out glxs_ver_rc -- git-lex-serve --version

# ---------------------------------------------------------------------------
# Post-run residue guard (AFTER)
# ---------------------------------------------------------------------------

guard_residue "after"

after_dotlex=$(residue_state ".lex")
after_squad=$(residue_state "Squad")
after_raw=$(residue_state "Raw")
after_artifacts=$(residue_state ".artifacts")

# ---------------------------------------------------------------------------
# Assemble version-gap flag
# ---------------------------------------------------------------------------

version_gap_confirmed="false"
if [[ "$glx_ver_rc" == "2" && "$glxs_ver_rc" == "2" ]]; then
  version_gap_confirmed="true"
fi

# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# ---------------------------------------------------------------------------
# Write install-proof.json (durable repository-relative evidence anchor)
# ---------------------------------------------------------------------------

# Escape any double-quotes/backslashes in captured output fields we embed.
# Only embed short, known-safe observed-output strings; rc values are integers.
esc() {
  # Escape \ " and control newlines for safe JSON string embedding.
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

cat > "$PROOF_JSON" <<JSON
{
  "schema_version": "m065-s02-install-proof/v1",
  "timestamp": "${timestamp}",
  "purpose": "Stage-2 cold-PATH install proof: proves the release-installed git-lex and git-lex-serve resolve through an explicit cold PATH (no vendor-dir) from /tmp, the git 'lex' subcommand dispatches to the installed git-lex binary, --version exits 2 (version gap, no version claim), and the main law-nexus checkout has no R047 residue before or after. Second empirical install-proof (resolution through PATH; binary identity is T01's install-manifest.json).",
  "cold_path_definition": {
    "path": "${COLD_PATH}",
    "cwd": "${COLD_CWD}",
    "invocation": "env -i HOME=/root PATH=<cold-path> <command>  (run from ${COLD_CWD})",
    "vendor_dir_excluded": true,
    "note": "explicit cold PATH containing ~/.cargo/bin and standard system dirs; does NOT contain /root/vendor-source/git-lex, /root/vendor-source/git-lex/target/debug, or any source/target path"
  },
  "proofs": {
    "path_resolution": {
      "git_lex_command_v_rc": ${glx_cv_rc},
      "git_lex_resolved_path": "$(esc "$glx_cv_out")",
      "git_lex_serve_command_v_rc": ${glxs_cv_rc},
      "git_lex_serve_resolved_path": "$(esc "$glxs_cv_out")",
      "evidence": "command -v under cold env resolves both binaries to the cargo bin dir, matching the T01 install-manifest.json binary paths"
    },
    "git_lex_direct_help": {
      "command": "git-lex --help",
      "exit_code": ${glx_help_rc},
      "banner_marker": "${BANNER_GIT_LEX}",
      "banner_found": ${glx_help_found},
      "evidence": "direct binary resolution through cold PATH; the installed git-lex ran and printed its banner"
    },
    "git_lex_serve_help": {
      "command": "git-lex-serve --help",
      "exit_code": ${glxs_help_rc},
      "banner_marker": "${BANNER_GIT_LEX_SERVE}",
      "banner_found": ${glxs_help_found},
      "evidence": "direct binary resolution through cold PATH (S01 contract section 5 item 3 satisfied)"
    },
    "git_lex_help_via_dispatch": {
      "command": "git lex --help",
      "exit_code": ${glx_dispatch_help_rc},
      "observed_output": "$(esc "$glx_dispatch_help_out")",
      "is_gate": false,
      "note": "git intercepts --help for EXTERNAL subcommands and routes it to man(1); with no man page installed, this prints 'No manual entry for git-lex' and exits non-zero (observed rc=${glx_dispatch_help_rc}). This is git's documented external-subcommand help-dispatch behavior, NOT an install defect, and it proves git recognizes 'lex' as a dispatchable subcommand (a non-existent subcommand yields rc=1 'is not a git command' — see contrast). The banner is NOT shown via this path because git never passes --help to the external binary. Contract section 5 item 2 ('git lex --help exits 0') assumed pass-through; the actual git dispatch routes --help to man. The cold-PATH resolution + dispatch INTENT is proven by git_lex_direct_help + git_subcommand_dispatch."
    },
    "git_subcommand_dispatch": {
      "primary_command": "git lex",
      "primary_exit_code": ${glx_noargs_rc},
      "primary_banner_marker": "${BANNER_GIT_LEX}",
      "primary_banner_found": ${glx_noargs_found},
      "primary_evidence": "git found git-lex via cold-PATH lookup and dispatched the 'lex' subcommand; git-lex ran with no args, so clap printed the banner + usage and exited 2 (missing required subcommand). Banner presence proves the installed git-lex binary executed (S01 contract section 5 item 4 satisfied).",
      "secondary_command": "git lex --version",
      "secondary_exit_code": ${glx_ver_rc},
      "secondary_evidence": "clap error 'unexpected argument --version found ... Usage: git-lex <COMMAND>' references git-lex, proving the dispatched binary was the installed git-lex.",
      "contrast_command": "git __nosuchcmd_xyz__ --help",
      "contrast_exit_code": ${contrast_rc},
      "contrast_evidence": "non-existent subcommand -> rc=1 'is not a git command'; 'lex' dispatches (rc=2, banner present), confirming lex IS a resolved subcommand, not a not-found case."
    },
    "version_gap": {
      "git_lex_version_command": "git lex --version",
      "git_lex_version_rc": ${glx_ver_rc},
      "git_lex_serve_version_command": "git-lex-serve --version",
      "git_lex_serve_version_rc": ${glxs_ver_rc},
      "version_gap_confirmed": ${version_gap_confirmed},
      "note": "contract prohibits version claim; --version exits 2 per M051/S09 and re-proven here. No version number is parsed or asserted."
    }
  },
  "residue_guard": {
    "before": {".lex": "${before_dotlex}", "Squad": "${before_squad}", "Raw": "${before_raw}", ".artifacts": "${before_artifacts}"},
    "after": {".lex": "${after_dotlex}", "Squad": "${after_squad}", "Raw": "${after_raw}", ".artifacts": "${after_artifacts}"},
    "r047_contract_phase": "honored"
  },
  "cli_install_only_boundary": {
    "wont": [
      "no main .lex init",
      "no R035/R037/R038 validation",
      "no ACP-kit source truth",
      "no single-repo/Stage-3 .lex adoption",
      "no serve/viz/listen server exposure",
      "no nuke/kit-update/save/create/join/raw mutating surfaces"
    ]
  }
}
JSON

log "wrote $PROOF_JSON"

# ---------------------------------------------------------------------------
# Self-verification: re-read the JSON and assert the real gate invariants.
# (git_lex_help_via_dispatch is intentionally NOT gated — see its note.)
# ---------------------------------------------------------------------------

python3 - "$PROOF_JSON" <<'PY'
import json, sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

errors = []

def check(cond, msg):
    if not cond:
        errors.append(msg)

proofs = data["proofs"]
cold = data["cold_path_definition"]

# cold PATH hygiene
check(cold["vendor_dir_excluded"] is True, "cold_path vendor_dir_excluded is not true")
check("/root/vendor-source/git-lex" not in cold["path"], "cold PATH contains vendor-source/git-lex")
check("/root/.cargo/bin" in cold["path"], "cold PATH missing ~/.cargo/bin")

# path resolution
pr = proofs["path_resolution"]
check(pr["git_lex_command_v_rc"] == 0, "command -v git-lex did not exit 0 under cold env")
check(pr["git_lex_serve_command_v_rc"] == 0, "command -v git-lex-serve did not exit 0 under cold env")
check(pr["git_lex_resolved_path"] == "/root/.cargo/bin/git-lex",
      f"git-lex resolved path unexpected: {pr['git_lex_resolved_path']!r}")
check(pr["git_lex_serve_resolved_path"] == "/root/.cargo/bin/git-lex-serve",
      f"git-lex-serve resolved path unexpected: {pr['git_lex_serve_resolved_path']!r}")

# direct help rc 0 + banner
d = proofs["git_lex_direct_help"]
check(d["exit_code"] == 0, f"git-lex --help exit_code != 0 (got {d['exit_code']})")
check(d["banner_found"] is True, "git-lex --help banner not found")

s = proofs["git_lex_serve_help"]
check(s["exit_code"] == 0, f"git-lex-serve --help exit_code != 0 (got {s['exit_code']})")
check(s["banner_found"] is True, "git-lex-serve --help banner not found")

# subcommand dispatch: primary git-lex dispatch rc 2 + banner present
disp = proofs["git_subcommand_dispatch"]
check(disp["primary_exit_code"] == 2,
      f"git lex (no args) primary dispatch exit_code != 2 (got {disp['primary_exit_code']})")
check(disp["primary_banner_found"] is True, "git lex (no args) dispatch banner not found")
check(disp["secondary_exit_code"] == 2,
      f"git lex --version secondary exit_code != 2 (got {disp['secondary_exit_code']})")
check(disp["contrast_exit_code"] == 1,
      f"contrast non-existent subcommand exit_code != 1 (got {disp['contrast_exit_code']})")

# version gap rc 2 for both, no version claim
vg = proofs["version_gap"]
check(vg["git_lex_version_rc"] == 2, f"git lex --version rc != 2 (got {vg['git_lex_version_rc']})")
check(vg["git_lex_serve_version_rc"] == 2,
      f"git-lex-serve --version rc != 2 (got {vg['git_lex_serve_version_rc']})")
check(vg["version_gap_confirmed"] is True, "version_gap_confirmed is not true")

# residue guard before + after all absent
rg = data["residue_guard"]
for phase in ("before", "after"):
    for name in (".lex", "Squad", "Raw", ".artifacts"):
        check(rg[phase][name] == "absent",
              f"residue {phase}/{name} is not absent (got {rg[phase][name]!r})")

# CLI-install-only boundary markers present
boundary = data["cli_install_only_boundary"]["wont"]
check(len(boundary) == 6, f"cli_install_only_boundary wont list length != 6 (got {len(boundary)})")

if errors:
    sys.stderr.write("[s02-proof] SELF-VERIFY FAILED:\n")
    for e in errors:
        sys.stderr.write(f"  - {e}\n")
    sys.exit(1)

print(f"[s02-proof] self-verify OK: {path}")
PY

log "self-verify passed"
log "DONE: cold-PATH install proof written and verified"
