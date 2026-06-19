#!/usr/bin/env bash
#
# scripts/s03-install-rehearsal-workflow-proof.sh
#
# M065-pqvr1r / S03 / T01 — Stage-2 isolated install-rehearsal workflow proof.
#
# Proves that the release-installed `git lex` command (S02: ~/.cargo/bin, cold
# PATH) executes a FULL init/sync/validate/query/list lifecycle in a SEPARATE
# disposable git repository (mktemp /tmp, trap-rm, OUTSIDE /root/law-nexus),
# under an EXPLICIT cold PATH that contains ~/.cargo/bin + system dirs but NO
# vendor-dir. This is the S01 install-contract section 5 item S03 acceptance:
# the installed command runs a real git-lex workflow (not just resolution).
#
# MEM549 inversion (the central hypothesis): with git-lex ON the cold PATH,
# `git lex init`'s auto-commit (`git commit -m 'git lex init'`) LANDS, because
# the installed pre-commit hook resolves `git-lex` via PATH lookup
# (command -v git-lex -> ~/.cargo/bin/git-lex) and runs `git-lex hook
# pre-commit` (extract + validate). This inverts M064, where the hook could
# NOT find git-lex (debug binary off PATH) and init's auto-commit silently left
# HEAD empty (main.rs auto-commit reports "did not succeed. Continuing.").
#
# Workflow proven (all in the disposable repo, every git-lex invocation under
# `env -i HOME=/root PATH=<cold> GIT_TERMINAL_PROMPT=0`, stdin from /dev/null):
#   1. residue guard BEFORE (.lex/Squad/Raw/.artifacts absent in main checkout)
#   2. mktemp disposable repo (assert NOT inside /root/law-nexus), trap-rm
#   3. git init + neutral LOCAL git identity (PII mitigation)
#   4. `git lex init`               -> rc 0; auto-commit lands; hook installed
#   5. seed notes/hello.md + plain `git commit` -> hook extract+validate; rc 0
#   6. `git lex sync`               -> rc 0 (build SPARQL store from git + .spo)
#   7. `git lex query --json "SELECT ?c WHERE { ?c a git:Commit }"` -> >=1 result
#   8. `git lex validate`           -> rc 0 (base-kit repo)
#   9. `git lex list --json`        -> rc 0
#  10. residue guard AFTER
#  11. write prd/architecture/acp/runtime/m065-s03/workflow-proof.json
#  12. embedded python3 self-verify (asserts the gate fields)
#
# Output: prd/architecture/acp/runtime/m065-s03/workflow-proof.json
#
# Idempotent + re-runnable (mktemp a fresh disposable each run, re-fetch the
# base kit from GitHub, rewrite workflow-proof.json). Network required (base
# kit GitHub fetch). Does NOT cd into /root/law-nexus, does NOT run git lex in
# the main checkout, does NOT run nuke/kit-update/save/create/join/raw or
# serve/viz/listen. CLI-install-only boundary preserved (section 6 of S01
# contract): no main .lex init, no R035/R037/R038 validation, no ACP-kit
# source truth, no single-repo/Stage-3 .lex adoption.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT="/root/law-nexus"
PROOF_DIR="$REPO_ROOT/prd/architecture/acp/runtime/m065-s03"
PROOF_JSON="$PROOF_DIR/workflow-proof.json"

# Explicit cold PATH: ~/.cargo/bin (S02 install target) + standard system dirs.
# Deliberately EXCLUDES /root/vendor-source/git-lex, .../target/debug, and any
# other source/target path so resolution can only come from the install target.
COLD_PATH="/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Pre-commit hook managed-section start marker (git-lex src/hooks.rs MARKER_START).
HOOK_MARKER="# --- git-lex managed (do not edit this section) ---"

# R047 contract-phase residue names that must stay absent in the main checkout.
RESIDUE_NAMES=(".lex" "Squad" "Raw" ".artifacts")

# Disposable repo path (created below via mktemp).
DISPOSABLE=""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log()  { printf '[s03-proof] %s\n' "$*" >&2; }
fail() { printf '[s03-proof] FATAL: %s\n' "$*" >&2; exit 1; }

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

residue_state() {
  local name="$1"
  if [[ -e "$REPO_ROOT/$name" ]]; then printf 'present'; else printf 'absent'; fi
}

# Residue guard. $1 = label ("before" | "after"). Exits 1 if any residue present.
guard_residue() {
  local label="$1" rc=0
  for name in "${RESIDUE_NAMES[@]}"; do
    if [[ -e "$REPO_ROOT/$name" ]]; then
      log "residue PRESENT ($label): $name"; rc=1
    fi
  done
  if [[ $rc -ne 0 ]]; then
    fail "R047 residue guard ($label) failed: residue present in main checkout"
  fi
  log "residue guard ($label): all four names absent (R047 honored)"
}

# Escape \ " and control chars for safe JSON string embedding.
esc() {
  local s="$1"
  s="${s//\\/\\\\}"; s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"; s="${s//$'\r'/\\r}"; s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

# Run under cold env from $DISPOSABLE; combined stdout+stderr -> LOGFILE; rc -> RC_VAR.
run_ws_log() {
  local logfile="$1"; shift
  local rc_var="$1"; shift
  [[ "${1:-}" == "--" ]] || fail "run_ws_log: expected '--' separator"
  shift
  local rc=0
  ( cd "$DISPOSABLE" && env -i HOME=/root PATH="$COLD_PATH" GIT_TERMINAL_PROMPT=0 "$@" >"$logfile" 2>&1 </dev/null ) || rc=$?
  printf -v "$rc_var" '%s' "$rc"
}

# Run under cold env from $DISPOSABLE; stdout -> OUTFILE, stderr -> ERRFILE; rc -> RC_VAR.
run_ws_split() {
  local outfile="$1"; shift
  local errfile="$1"; shift
  local rc_var="$1"; shift
  [[ "${1:-}" == "--" ]] || fail "run_ws_split: expected '--' separator"
  shift
  local rc=0
  ( cd "$DISPOSABLE" && env -i HOME=/root PATH="$COLD_PATH" GIT_TERMINAL_PROMPT=0 "$@" >"$outfile" 2>"$errfile" </dev/null ) || rc=$?
  printf -v "$rc_var" '%s' "$rc"
}

# First line of $1 matching ERE $2 (CR-stripped); empty string if none.
first_marker() {
  grep -m1 -E "$2" "$1" 2>/dev/null | tr -d '\r' || true
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

log "repo root: $REPO_ROOT"
log "proof json: $PROOF_JSON"
verify_cold_path
mkdir -p "$PROOF_DIR"

# ---------------------------------------------------------------------------
# Residue guard BEFORE
# ---------------------------------------------------------------------------

guard_residue "before"
before_dotlex=$(residue_state ".lex")
before_squad=$(residue_state "Squad")
before_raw=$(residue_state "Raw")
before_artifacts=$(residue_state ".artifacts")

# ---------------------------------------------------------------------------
# Disposable repo (mktemp /tmp, trap-rm, OUTSIDE /root/law-nexus)
# ---------------------------------------------------------------------------

DISPOSABLE="$(mktemp -d /tmp/s03-workflow-XXXXXX)"
cleanup() { [[ -n "${DISPOSABLE:-}" ]] && rm -rf "$DISPOSABLE"; }
trap cleanup EXIT
log "disposable repo: $DISPOSABLE"

# Assert the disposable repo is NOT inside the main law-nexus checkout.
case "$DISPOSABLE" in
  "/root/law-nexus"|"/root/law-nexus"/*) fail "disposable repo ($DISPOSABLE) is inside /root/law-nexus" ;;
esac
is_inside_main_law_nexus="false"

# ---------------------------------------------------------------------------
# git init + neutral LOCAL git identity (PII mitigation — Threat Surface flag)
# ---------------------------------------------------------------------------

run_ws_log "$DISPOSABLE/git-init.log" gitinit_rc -- git init -q
if [[ "$gitinit_rc" != "0" ]]; then
  cat "$DISPOSABLE/git-init.log" >&2 || true
  fail "git init failed (rc=$gitinit_rc)"
fi

run_ws_log "$DISPOSABLE/cfg-email.log" cfg_email_rc -- git config user.email "s03-workflow-proof@local"
[[ "$cfg_email_rc" == "0" ]] || fail "git config user.email failed (rc=$cfg_email_rc)"
run_ws_log "$DISPOSABLE/cfg-name.log" cfg_name_rc -- git config user.name "s03-workflow-proof"
[[ "$cfg_name_rc" == "0" ]] || fail "git config user.name failed (rc=$cfg_name_rc)"
log "git repo initialized with neutral local identity (s03-workflow-proof)"

# ---------------------------------------------------------------------------
# Stage: git lex init  (base kit GitHub fetch + hook install + auto-commit)
# ---------------------------------------------------------------------------

log "STAGE init: git lex init (cold PATH; base kit GitHub fetch) ..."
run_ws_log "$DISPOSABLE/init.log" init_rc -- git lex init
if [[ "$init_rc" != "0" ]]; then
  log "----- init.log -----"; cat "$DISPOSABLE/init.log" >&2 || true
  fail "git lex init exit_code=$init_rc (expected 0)"
fi
log "init exit_code=0"

# MEM549 inversion check: did init's auto-commit ('git lex init') land?
# init runs `git add .lex/` then `git commit -m 'git lex init'`; the commit
# triggers the freshly-installed pre-commit hook, which (with git-lex ON cold
# PATH) resolves git-lex and runs extract+validate, letting the commit land.
run_ws_log "$DISPOSABLE/init-git-log.log" initlog_rc -- git log --oneline
if [[ "$initlog_rc" != "0" ]]; then
  log "----- init-git-log.log -----"; cat "$DISPOSABLE/init-git-log.log" >&2 || true
  fail "git log after init failed (rc=$initlog_rc) — HEAD may be empty"
fi
init_commit_count=$(grep -c -F "git lex init" "$DISPOSABLE/init-git-log.log" || true)
if [[ "$init_commit_count" -ge 1 ]]; then auto_commit_landed="true"; else auto_commit_landed="false"; fi

hook_installed="false"
if [[ -f "$DISPOSABLE/.git/hooks/pre-commit" ]] && grep -q -F "$HOOK_MARKER" "$DISPOSABLE/.git/hooks/pre-commit"; then
  hook_installed="true"
fi

lex_dir_created="false"
[[ -d "$DISPOSABLE/.lex" ]] && lex_dir_created="true"

log "init: auto_commit_landed=$auto_commit_landed init_commit_count=$init_commit_count hook_installed=$hook_installed lex_dir_created=$lex_dir_created"

# Hard gates for the central hypothesis.
if [[ "$auto_commit_landed" != "true" ]]; then
  log "----- init.log -----"; cat "$DISPOSABLE/init.log" >&2 || true
  log "----- init-git-log.log -----"; cat "$DISPOSABLE/init-git-log.log" >&2 || true
  fail "MEM549 inversion FAILED: init auto-commit did NOT land (pre-commit hook could not run git-lex)"
fi
[[ "$hook_installed" == "true" ]] || fail "pre-commit hook managed marker not found after init"
[[ "$lex_dir_created" == "true" ]] || fail ".lex/ directory not created after init"

# ---------------------------------------------------------------------------
# Stage: seed one content doc + plain git commit (triggers hook extract+validate)
# NOT `git lex save` / `git lex create` — both on the denylist (section 6).
# ---------------------------------------------------------------------------

mkdir -p "$DISPOSABLE/notes"
printf -- '---\nfm.title: hello\nfm.tags: probe\n---\n# hello\nworkflow probe.\n' > "$DISPOSABLE/notes/hello.md"

run_ws_log "$DISPOSABLE/add.log" add_rc -- git add notes/hello.md
if [[ "$add_rc" != "0" ]]; then cat "$DISPOSABLE/add.log" >&2 || true; fail "git add notes/hello.md failed (rc=$add_rc)"; fi

log "STAGE content_seed_commit: git commit -m 'add note' (hook runs extract+validate) ..."
run_ws_log "$DISPOSABLE/content-commit.log" content_commit_rc -- git commit -m 'add note'
if [[ "$content_commit_rc" != "0" ]]; then
  log "----- content-commit.log -----"; cat "$DISPOSABLE/content-commit.log" >&2 || true
  fail "content seed git commit exit_code=$content_commit_rc (expected 0 — hook extract+validate should pass for a base-kit fm doc)"
fi
log "content_seed_commit exit_code=0 (hook extract+validate passed)"

# Did the hook extract a .spo sidecar for notes/hello.md?
spo_total="$(find "$DISPOSABLE/.lex/extract" -type f -name '*.spo' 2>/dev/null | wc -l | tr -d ' ')"
hello_spo_path="$(find "$DISPOSABLE/.lex/extract" -type f -name '*.spo' 2>/dev/null -exec grep -l -F 'hello' {} \; 2>/dev/null | head -n1 || true)"
if [[ -n "$hello_spo_path" ]]; then hook_extracted_spo="true"; else hook_extracted_spo="false"; fi
# commit rc 0 => the pre-commit hook (extract + validate) passed.
hook_validate_passed="true"

log "content_seed_commit: hook_extracted_spo=$hook_extracted_spo (spo_total=$spo_total) hook_validate_passed=$hook_validate_passed"

# ---------------------------------------------------------------------------
# Stage: git lex sync  (build SPARQL store from git history + .spo sidecars)
# ---------------------------------------------------------------------------

log "STAGE sync: git lex sync ..."
run_ws_log "$DISPOSABLE/sync.log" sync_rc -- git lex sync
if [[ "$sync_rc" != "0" ]]; then
  log "----- sync.log -----"; cat "$DISPOSABLE/sync.log" >&2 || true
  fail "git lex sync exit_code=$sync_rc (expected 0)"
fi
sync_marker="$(first_marker "$DISPOSABLE/sync.log" 'graph|sync|commit|quad|Virtual|event|assertion|now')"
[[ -n "$sync_marker" ]] || sync_marker="$(grep -m1 -v -E '^[[:space:]]*$' "$DISPOSABLE/sync.log" | tr -d '\r' || true)"
log "sync exit_code=0 marker=$(printf '%s' "$sync_marker" | head -c 120)"

# ---------------------------------------------------------------------------
# Stage: git lex query --json  (>=1 git:Commit binding proves store is queryable)
# ---------------------------------------------------------------------------

log 'STAGE query: git lex query --json "SELECT ?c WHERE { ?c a git:Commit }" ...'
run_ws_split "$DISPOSABLE/query.stdout" "$DISPOSABLE/query.stderr" query_rc -- \
  git lex query --json "SELECT ?c WHERE { ?c a git:Commit }"
if [[ "$query_rc" != "0" ]]; then
  log "----- query.stdout -----"; cat "$DISPOSABLE/query.stdout" >&2 || true
  log "----- query.stderr -----"; cat "$DISPOSABLE/query.stderr" >&2 || true
  fail "git lex query exit_code=$query_rc (expected 0)"
fi
commit_results_count=$(SPARQL_FILE="$DISPOSABLE/query.stdout" python3 - <<'PY'
import json, os
raw = open(os.environ["SPARQL_FILE"]).read()
dec = json.JSONDecoder()
i = raw.find("{"); n = 0
if i >= 0:
    try:
        d, _ = dec.raw_decode(raw[i:])
        b = (d.get("results") or {}).get("bindings") or d.get("bindings") or []
        n = len(b)
    except Exception:
        n = 0
print(n)
PY
)
log "query exit_code=0 commit_results_count=$commit_results_count"
if [[ "$commit_results_count" -lt 1 ]]; then
  log "----- query.stdout -----"; cat "$DISPOSABLE/query.stdout" >&2 || true
  log "----- query.stderr -----"; cat "$DISPOSABLE/query.stderr" >&2 || true
  fail "query returned $commit_results_count git:Commit results (expected >=1 — store not built or query shape wrong)"
fi

# ---------------------------------------------------------------------------
# Stage: git lex validate  (rc 0 in a base-kit repo with one fm doc)
# ---------------------------------------------------------------------------

log "STAGE validate: git lex validate ..."
run_ws_log "$DISPOSABLE/validate.log" validate_rc -- git lex validate
if [[ "$validate_rc" != "0" ]]; then
  log "----- validate.log -----"; cat "$DISPOSABLE/validate.log" >&2 || true
  fail "git lex validate exit_code=$validate_rc (expected 0 — base-kit fm doc should pass)"
fi
validate_marker="$(first_marker "$DISPOSABLE/validate.log" 'Validated|pass|violation')"
[[ -n "$validate_marker" ]] || validate_marker="$(grep -m1 -v -E '^[[:space:]]*$' "$DISPOSABLE/validate.log" | tr -d '\r' || true)"
log "validate exit_code=0 marker=$(printf '%s' "$validate_marker" | head -c 120)"

# ---------------------------------------------------------------------------
# Stage: git lex list --json  (rc 0; classes_count is recorded, not gated)
# ---------------------------------------------------------------------------

log "STAGE list: git lex list --json ..."
run_ws_split "$DISPOSABLE/list.stdout" "$DISPOSABLE/list.stderr" list_rc -- git lex list --json
if [[ "$list_rc" != "0" ]]; then
  log "----- list.stdout -----"; cat "$DISPOSABLE/list.stdout" >&2 || true
  log "----- list.stderr -----"; cat "$DISPOSABLE/list.stderr" >&2 || true
  fail "git lex list exit_code=$list_rc (expected 0)"
fi
classes_count=$(LIST_FILE="$DISPOSABLE/list.stdout" python3 - <<'PY'
import json, os
raw = open(os.environ["LIST_FILE"]).read()
dec = json.JSONDecoder()
n = 0
i = raw.find("[")
if i >= 0:
    try:
        d, _ = dec.raw_decode(raw[i:])
        n = len(d) if isinstance(d, list) else 0
    except Exception:
        n = 0
else:
    i = raw.find("{")
    if i >= 0:
        try:
            d, _ = dec.raw_decode(raw[i:])
            c = d.get("classes")
            n = len(c) if isinstance(c, list) else 0
        except Exception:
            n = 0
print(n)
PY
)
log "list exit_code=0 classes_count=$classes_count"

# ---------------------------------------------------------------------------
# Residue guard AFTER
# ---------------------------------------------------------------------------

guard_residue "after"
after_dotlex=$(residue_state ".lex")
after_squad=$(residue_state "Squad")
after_raw=$(residue_state "Raw")
after_artifacts=$(residue_state ".artifacts")

# ---------------------------------------------------------------------------
# Timestamp + write workflow-proof.json
# ---------------------------------------------------------------------------

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

cat > "$PROOF_JSON" <<JSON
{
  "schema_version": "m065-s03-workflow-proof/v1",
  "timestamp": "${timestamp}",
  "purpose": "Stage-2 isolated install-rehearsal workflow proof: the release-installed git lex command (S02 ~/.cargo/bin) executes a full init/sync/validate/query/list lifecycle in a separate disposable git repository (mktemp /tmp, OUTSIDE /root/law-nexus) under an explicit cold PATH with no vendor-dir. MEM549 inversion: with git-lex on cold PATH, git lex init's auto-commit LANDS because the installed pre-commit hook resolves git-lex via PATH lookup and runs extract+validate (inverting M064, where the hook could not find git-lex and HEAD stayed empty).",
  "cold_path_definition": {
    "path": "${COLD_PATH}",
    "env": "env -i HOME=/root PATH=<cold-path> GIT_TERMINAL_PROMPT=0  (each git-lex invocation)",
    "cwd_invocation": "every cold invocation runs from the disposable repo via ( cd \$DISPOSABLE && env -i ... ); stdin redirected from /dev/null to absorb any interactive prompt",
    "vendor_dir_excluded": true,
    "note": "explicit cold PATH containing ~/.cargo/bin and standard system dirs; does NOT contain /root/vendor-source/git-lex, /root/vendor-source/git-lex/target/debug, or any source/target path"
  },
  "disposable_repo": {
    "path": "${DISPOSABLE}",
    "is_inside_main_law_nexus": ${is_inside_main_law_nexus},
    "git_init_rc": ${gitinit_rc},
    "trap_rm_on_exit": true,
    "git_identity": "local neutral identity (s03-workflow-proof@local) — PII mitigation"
  },
  "stages": {
    "init": {
      "command": "git lex init",
      "exit_code": ${init_rc},
      "auto_commit_landed": ${auto_commit_landed},
      "init_commit_count": ${init_commit_count},
      "lex_dir_created": ${lex_dir_created},
      "hook_installed": ${hook_installed},
      "hook_marker": "$(esc "$HOOK_MARKER")",
      "evidence": "git lex init (default base kit repolex-ai/git-lex-kit-base, GitHub fetch) exited 0; the installed pre-commit hook resolved git-lex via cold-PATH lookup (command -v git-lex) and ran git-lex hook pre-commit (extract + validate), so init's auto-commit ('git lex init') landed — the MEM549 inversion vs M064 (where the hook could not find git-lex and HEAD stayed empty)."
    },
    "content_seed_commit": {
      "command": "git add notes/hello.md && git commit -m 'add note'",
      "exit_code": ${content_commit_rc},
      "hook_extracted_spo": ${hook_extracted_spo},
      "spo_total": ${spo_total},
      "hook_validate_passed": ${hook_validate_passed},
      "note": "plain git commit (NOT git lex save / git lex create — both on the denylist) triggers the pre-commit hook, which extracts notes/hello.md frontmatter into a .spo sidecar and validates it. exit_code 0 means the hook's extract+validate passed."
    },
    "sync": {
      "command": "git lex sync",
      "exit_code": ${sync_rc},
      "output_marker": "$(esc "$sync_marker")",
      "evidence": "git lex sync built the SPARQL store (.git/lex/oxigraph) from git history + .spo sidecars; exit 0."
    },
    "query": {
      "command": "git lex query --json \"SELECT ?c WHERE { ?c a git:Commit }\"",
      "exit_code": ${query_rc},
      "commit_results_count": ${commit_results_count},
      "proof_strength": "operational-runtime",
      "evidence": "after init + content commits and sync, the installed git lex query returned >=1 git:Commit binding, proving the store is built and queryable through the installed command (git: prefix is injected; git:Commit data triples are in the store)."
    },
    "validate": {
      "command": "git lex validate",
      "exit_code": ${validate_rc},
      "output_marker": "$(esc "$validate_marker")",
      "evidence": "git lex validate exited 0 in the base-kit disposable repo (one fm doc fm.title/fm.tags; base kit has install folders:false so no type-folder content; no adaptive overlay)."
    },
    "list": {
      "command": "git lex list --json",
      "exit_code": ${list_rc},
      "classes_count": ${classes_count},
      "evidence": "git lex list --json exited 0; classes_count is the discovered-class array length (base kit install folders:false -> may be 0 content classes; only rc 0 is gated)."
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
  },
  "known_out_of_checkout_side_effects": {
    "machine_registry": "~/.lex/repos (global git-lex per-machine registry, mutated by every init; lives in HOME, NOT in the law-nexus checkout; not R047 residue)",
    "note": "the disposable repo and its .lex/.git state are trap-rm'd on exit. The only durable out-of-checkout side effect is the global ~/.lex/repos registry entry, which is expected git-lex behavior and is not R047 residue."
  }
}
JSON

log "wrote $PROOF_JSON"

# ---------------------------------------------------------------------------
# Self-verification: re-read the JSON and assert the real gate invariants.
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

cold = data["cold_path_definition"]
disp = data["disposable_repo"]
stages = data["stages"]

# cold PATH hygiene
check(cold["vendor_dir_excluded"] is True, "cold_path vendor_dir_excluded is not true")
check("/root/vendor-source/git-lex" not in cold["path"], "cold PATH contains vendor-source/git-lex")
check("/root/.cargo/bin" in cold["path"], "cold PATH missing ~/.cargo/bin")

# disposable repo isolation
check(disp["is_inside_main_law_nexus"] is False, "disposable repo reported inside main checkout")
check(disp["git_init_rc"] == 0, f"git_init_rc != 0 (got {disp['git_init_rc']})")

# init — MEM549 inversion
init = stages["init"]
check(init["exit_code"] == 0, f"init exit_code != 0 (got {init['exit_code']})")
check(init["auto_commit_landed"] is True, "init auto_commit_landed is not true (MEM549 inversion failed)")
check(init["init_commit_count"] >= 1, f"init_commit_count < 1 (got {init['init_commit_count']})")
check(init["hook_installed"] is True, "init hook_installed is not true")
check(init["lex_dir_created"] is True, "init lex_dir_created is not true")

# content seed commit
csc = stages["content_seed_commit"]
check(csc["exit_code"] == 0, f"content_seed_commit exit_code != 0 (got {csc['exit_code']})")
check(csc["hook_extracted_spo"] is True, "content_seed_commit hook_extracted_spo is not true")
check(csc["hook_validate_passed"] is True, "content_seed_commit hook_validate_passed is not true")

# sync
sync = stages["sync"]
check(sync["exit_code"] == 0, f"sync exit_code != 0 (got {sync['exit_code']})")

# query
q = stages["query"]
check(q["exit_code"] == 0, f"query exit_code != 0 (got {q['exit_code']})")
check(q["commit_results_count"] >= 1, f"query commit_results_count < 1 (got {q['commit_results_count']})")

# validate
v = stages["validate"]
check(v["exit_code"] == 0, f"validate exit_code != 0 (got {v['exit_code']})")

# list
lst = stages["list"]
check(lst["exit_code"] == 0, f"list exit_code != 0 (got {lst['exit_code']})")

# residue guard before + after all absent
rg = data["residue_guard"]
for phase in ("before", "after"):
    for name in (".lex", "Squad", "Raw", ".artifacts"):
        check(rg[phase][name] == "absent", f"residue {phase}/{name} is not absent (got {rg[phase][name]!r})")
check(rg["r047_contract_phase"] == "honored", "r047_contract_phase != honored")

# CLI-install-only boundary markers present
boundary = data["cli_install_only_boundary"]["wont"]
check(len(boundary) == 6, f"cli_install_only_boundary wont length != 6 (got {len(boundary)})")

# known out-of-checkout side effects documented
kse = data["known_out_of_checkout_side_effects"]
check("machine_registry" in kse, "known_out_of_checkout_side_effects missing machine_registry")

if errors:
    sys.stderr.write("[s03-proof] SELF-VERIFY FAILED:\n")
    for e in errors:
        sys.stderr.write(f"  - {e}\n")
    sys.exit(1)

print(f"[s03-proof] self-verify OK: {path}")
PY

log "self-verify passed"
log "DONE: isolated install-rehearsal workflow proof written and verified"
