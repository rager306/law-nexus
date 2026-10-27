---
id: T001
title: Vendor the pinned runtime and make CI restore it honestly with shipped-main governor proof and failure diagnostics
wave: 1
deps: [T002]
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - .ai/vendor/gsd-path-1.6.2.tgz
  - .github/workflows/repository-quality.yml
  - tests/test_ci_runtime_restore.py
  - scripts/install.py
  - .gitignore
---

# T001 — Vendor the pinned runtime and make CI restore it honestly with shipped-main governor proof and failure diagnostics

## Context

CI run 40446077586 on main@4e0cd4db: the migration job's real governor step exits 1 `runtime-unavailable` — the pinned runtime 1.6.2@6f95a31e is machine-local (`~/.gsd-path/runtimes/<digest>/`), CI never restores it, and the step redirects stdout into `governor.json`, which is never published, so the only visible signal is a bare non-zero exit. The runtime source exists in the repository checkout only under gitignored `.ai/local/vendor/gsd-path/` (verified 2026-10-27: package metadata `.ai-install.json` names path 1.6.2). This task vendors it and ships the installer: the pure-stdlib `scripts/install.py` (no npm needed) is CREATED by this task — planned contract, rehearsal-validated 2026-10-27 by the planner against the local store: on a matching source it exits 0 printing `runtime: restore 1.6.2 (6f95a31e…) (dry run)`, on a doctored source it aborts with `error: source does not match declared runtime 1.6.2 (6f95a31e…); use its matching package` — that digest pair is E1's held-out test. PR-triggered runs check out a detached merge ref where the documented fail-closed branch ownership fires; the INTENT acceptance surface is the push-to-main run, so a red PR run with published diagnostics is documented honest behavior, not a defect to suppress (N3).

## Approach

Contract constraints (the binding shapes are in Interface contract):

- `WorkflowStateKind.SHIPPED_INTEGRATED` — `law_nexus_harness.workflow_state.WorkflowStateKind` member with value `"shipped-integrated"`.
- Classification (`read_workflow_state`): when the native status payload has `route.action == "block"` AND `completion.status == "verified"` AND `state.phase == "shipped"` AND `state.status == "done"`, the report kind is `SHIPPED_INTEGRATED` (non-blocking; remediation `"none"`); `report.observed` names the shipped/done outcome and the payload's `state.archive` path. Every other non-operational route stays `CONFLICTING_OWNERSHIP`. A present-but-wrongly-typed `completion` field fails closed to `invalid-schema` (same discipline as the four existing identity sites).
- `workflow_readiness(SHIPPED_INTEGRATED)` returns `"operational"`.
- Governor finding (`check_workflow_state_surface`): `check_id "workflow-state-surface"`, `status "pass"`, `severity "ok"`, `rule_id "workflow-state-surface.shipped"`, `observed` starts with `"kind=shipped-integrated;"` and contains the archive path (`.project/archive/001-001-native-workflow-acceptance` on integrated M001 main).
- Preflight check (`_workflow_state_surface_check`): `check_id "workflow-state-surface"`, `status "pass"`, `observed` contains `"state=shipped-integrated"` and the archive path.

- Vendored archive: `.ai/vendor/gsd-path-1.6.2.tgz` — a tar.gz whose single top-level directory `gsd-path/` contains `package.json` and `scripts/` of the pinned 1.6.2 GSD Path release; its content digest-matches `.gsd-path/runtime.json` (`{"version": "1.6.2", "digest": "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"}`).
- Restore procedure (the documented bootstrap command): `tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C <temporary-dir>` then `python3 <temporary-dir>/gsd-path/scripts/install.py --runtime-restore --project <repo-root> --source-root <temporary-dir>/gsd-path`. Exit 0 = the pinned runtime is installed or reused idempotently; non-zero = loud failure carrying the recorded version+digest pair. The extraction target is always a temporary directory, never a tracked path.
- Diagnostics: when the migration job's governor step fails, it publishes a workflow artifact named `governor-diagnostics` containing `governor.json` and prints the report JSON to the job log; the job exit stays non-zero. A passing run publishes no artifact.
- Shipped-main CI assertion: on a push-to-main run the governor step requires governor exit 0 and its report's `workflow-state-surface` observed to contain `"kind=shipped-integrated;"` and `".project/archive/001-001-native-workflow-acceptance"`.

## Interface contract

- `WorkflowStateKind.SHIPPED_INTEGRATED` — `law_nexus_harness.workflow_state.WorkflowStateKind` member with value `"shipped-integrated"`.
- Classification (`read_workflow_state`): when the native status payload has `route.action == "block"` AND `completion.status == "verified"` AND `state.phase == "shipped"` AND `state.status == "done"`, the report kind is `SHIPPED_INTEGRATED` (non-blocking; remediation `"none"`); `report.observed` names the shipped/done outcome and the payload's `state.archive` path. Every other non-operational route stays `CONFLICTING_OWNERSHIP`. A present-but-wrongly-typed `completion` field fails closed to `invalid-schema` (same discipline as the four existing identity sites).
- `workflow_readiness(SHIPPED_INTEGRATED)` returns `"operational"`.
- Governor finding (`check_workflow_state_surface`): `check_id "workflow-state-surface"`, `status "pass"`, `severity "ok"`, `rule_id "workflow-state-surface.shipped"`, `observed` starts with `"kind=shipped-integrated;"` and contains the archive path (`.project/archive/001-001-native-workflow-acceptance` on integrated M001 main).
- Preflight check (`_workflow_state_surface_check`): `check_id "workflow-state-surface"`, `status "pass"`, `observed` contains `"state=shipped-integrated"` and the archive path.

- Vendored archive: `.ai/vendor/gsd-path-1.6.2.tgz` — a tar.gz whose single top-level directory `gsd-path/` contains `package.json` and `scripts/` of the pinned 1.6.2 GSD Path release; its content digest-matches `.gsd-path/runtime.json` (`{"version": "1.6.2", "digest": "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"}`).
- Restore procedure (the documented bootstrap command): `tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C <temporary-dir>` then `python3 <temporary-dir>/gsd-path/scripts/install.py --runtime-restore --project <repo-root> --source-root <temporary-dir>/gsd-path`. Exit 0 = the pinned runtime is installed or reused idempotently; non-zero = loud failure carrying the recorded version+digest pair. The extraction target is always a temporary directory, never a tracked path.
- Diagnostics: when the migration job's governor step fails, it publishes a workflow artifact named `governor-diagnostics` containing `governor.json` and prints the report JSON to the job log; the job exit stays non-zero. A passing run publishes no artifact.
- Shipped-main CI assertion: on a push-to-main run the governor step requires governor exit 0 and its report's `workflow-state-surface` observed to contain `"kind=shipped-integrated;"` and `".project/archive/001-001-native-workflow-acceptance"`.

## Intent coverage

- SC1
- SC3

## Acceptance criteria

1. `.ai/vendor/gsd-path-1.6.2.tgz` is tracked, contains a single top-level `gsd-path/` with `package.json` and `scripts/`, and the installer dry-run against its extracted content exits 0 printing the pinned pair `1.6.2 (6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f)` (E2: an already-valid store is reused untouched — the restore is idempotent by the installer's contract).
2. Both `migration-layer-quality` and `rust-harness-quality` restore the pinned runtime from the vendored archive, per Contract B, before any operational check; a missing archive or a digest mismatch fails the job loudly with the recorded version+digest pair; no suppression is added around restore or governor exits (E1, N1, N3).
3. On governor failure the step prints the report JSON to the job log and publishes the `governor-diagnostics` artifact; on success it publishes no artifact; the job exit stays non-zero on failure (SC3, E5).
4. On a push-to-main run the governor step requires exit 0 and the report's workflow-state-surface observed to contain `kind=shipped-integrated;` and `.project/archive/001-001-native-workflow-acceptance`; any other main outcome fails the step (SC1).
5. `tests/test_ci_runtime_restore.py` pins the installer digest behavior and the workflow wiring above and passes via this task's Verify.

## Verify

```bash
uv run --frozen pytest tests/test_ci_runtime_restore.py -q
```
<!-- Fails if the vendored archive is missing or digest-drifted, if a restore step, the
     diagnostics artifact, or the shipped-main assertion is removed, or if any
     suppression appears around restore/governor exits. -->

Heavy: no

## Log

<!-- Append-only: coder summary, blocks (`NEEDS-ORCHESTRATOR: <question> —
     readings: <candidates>` for contract ambiguity), orchestrator answers,
     review verdicts, fixes. -->
- 2026-10-27 — created by planner
- 2026-10-27 — plan-defect repair (orchestrator, per the approve lint): the Context referenced `scripts/install.py`
  as an existing rehearsed artifact; reframed as a task deliverable (created by this task, listed in `files`),
  with the rehearsal preserved as the validated approach description. Flagged by approve's brief path check.

- 2026-10-27 — implemented by build_T001 (base 86787121, worktree gsd-path-task/T001).
  - `.ai/vendor/gsd-path-1.6.2.tgz` (427 KB, 48 members): single top-level `gsd-path/` carrying
    `package.json` plus the full `scripts/` of the pinned 1.6.2 release from the machine-local
    `.ai/local/vendor/gsd-path/`; its 32 digest-relevant runtime scripts reproduce the pinned digest exactly
    (recomputed `6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f` == `.gsd-path/runtime.json`).
    `.ai-install.json` inspected as vendor-source provenance (path 1.6.2, npm sha512 SRI); not packed — not part
    of the task's archive content contract. Packed deterministically (sorted names, uid/gid 0, fixed mtime).
  - `scripts/install.py` (new): standalone pure-stdlib restorer reusing the release's own verification and
    publication algorithm (verbatim RUNTIME_FILES inventory, per-file sha256, sorted-JSON manifest digest,
    validate_runtime semantics incl. __pycache__ tolerance, staged atomic publish, idempotent valid-store reuse,
    git-root check) with the rehearsed CLI and byte-exact output contract. A byte-copy of the release installer
    was rejected: it fails the repository ruff config (pyproject `include: scripts/**/*.py`; pre-commit lints
    staged scripts) and cannot run outside the release tree. The archive carries this tracked installer at
    `gsd-path/scripts/install.py`; the installer is not digest-covered, and the release's digest-relevant files
    are packed verbatim.
  - `.github/workflows/repository-quality.yml`: `migration-layer-quality` and `rust-harness-quality` both
    restore the pinned runtime from the vendored archive before any operational check; missing archive or digest
    mismatch fails the job loudly with the recorded version+digest pair; no suppression around restore or
    governor exits. Governor step pipes the report through `tee` under `pipefail` (printed to the job log, file
    kept, exit preserved) and on push-to-main requires the `workflow-state-surface` observed to carry
    `kind=shipped-integrated;` and `.project/archive/001-001-native-workflow-acceptance`. New failure-only step
    publishes the `governor-diagnostics` artifact (`if: failure()`, `if-no-files-found: error`); a passing run
    publishes nothing. `tests/test_ci_runtime_restore.py` added to the migration pytest list.
  - Shipped-main proof inputs wired: migration job checkout `fetch-depth: 0` and an explicit
    `git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main` step. Grounded in a live probe (named
    branch at integrated main 4e0cd4db, runtime restored from the vendored archive, origin pointing at GitHub):
    native completion verdict `verified` (ship 886a36a8, integrate 4e0cd4db, archive
    `.project/archive/001-001-native-workflow-acceptance`), route `block` only on branch ownership, governor
    exit 0 `status: ok` (72 pass) with finding `workflow-state-surface.shipped`, observed starting
    `kind=shipped-integrated;` and naming the archive path. The completion proof reads origin/main first-parent
    history, `refs/remotes/origin/HEAD`, and live `git ls-remote origin` — without full history and origin/HEAD a
    real push-to-main run cannot verify it. Earlier probe failures were clone-environment artifacts only
    (colliding local `gsd-path-task/T001`, origin/HEAD on the task branch, stale local `main` as the
    remote-tracking ref); each was reproduced and eliminated before the final verdict.
  - Rehearsal in sandboxed HOME: fresh restore exits 0 printing `runtime: restore 1.6.2 (6f95a31e…)`; second run
    reuses the store byte-identically (E2); doctored source exits 1 printing `error: source does not match
    declared runtime 1.6.2 (6f95a31e…); use its matching package` (E1); dry run prints the pinned pair with
    "(dry run)"; the freshly published store (32 files + manifest.json) passes the harness's own
    `.gsd-path/status_runtime.py` validate_runtime; the exact CI restore step text was executed byte-for-byte
    (fresh-install path, and the missing-archive guard path which fails loudly naming the archive and the
    recorded pair).
  - Boundary note: two edit-tool mishaps briefly created untracked `scripts/install.py` and
    `tests/test_ci_runtime_restore.py` in the primary worktree (/root/law-nexus) before the isolated-worktree
    paths were used; both were moved into this task worktree within the same minute and the primary was restored
    to its prior state (only pre-existing orchestrator dispatch records remain untracked there). No tracked
    primary file was read-modified; nothing else was written there.
- 2026-10-27 — Verify: `uv run --frozen pytest tests/test_ci_runtime_restore.py -q` → `15 passed in 1.16s`
  (exit 0). Also green: `ruff check` + `ruff format --check` on `scripts/install.py` and
  `tests/test_ci_runtime_restore.py`; `tests/test_repository_quality_gate.py` 5 passed against the edited
  workflow.
- 2026-10-27 — NEEDS-ORCHESTRATOR: `.gitignore:105` rule `vendor/` ignores `.ai/vendor/`, so the declared
  deliverable `.ai/vendor/gsd-path-1.6.2.tgz` can never be tracked (`git add` skips ignored paths; a CI checkout
  would never contain it, making the restore step's missing-archive guard fire on every run) — authorize adding
  the surgical negation `!/.ai/vendor/` after the `vendor/` rule (and adding `.gitignore` to this task's files,
  or applying the one-liner yourself)? — readings: (1) negation `!/.ai/vendor/` in `.gitignore` keeps the
  broad `vendor/` rule intact for every other tree and un-excludes exactly the contract-pinned archive path;
  (2) relocate the archive to a non-ignored tracked path — rejected as a coder option because the path is
  verbatim in this task's and T005's Interface contracts, PLAN.md's dependency note, and the workflow restore
  command; (3) stage the file once with `git add -f` at commit time — works exactly once, leaves the artifact
  ignored thereafter and the "tracked archive" claim unenforceable by normal flow.

- 2026-10-27 — orchestrator answer + plan-defect repair (owner standing delegation; same class as the M001 gitignore anchoring): .gitignore joins `files`; Add the surgical negation `!/.ai/vendor/` immediately after the existing `vendor/` rule in `.gitignore`
  (nothing else in the file changes) so the declared archive is trackable; pack the archive into the tracked
  path; keep the restore step and its tests as implemented.
