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
---

# T001 — Vendor the pinned runtime and make CI restore it honestly with shipped-main governor proof and failure diagnostics

## Context

CI run 40446077586 on main@4e0cd4db: the migration job's real governor step exits 1 `runtime-unavailable` — the pinned runtime 1.6.2@6f95a31e is machine-local (`~/.gsd-path/runtimes/<digest>/`), CI never restores it, and the step redirects stdout into `governor.json`, which is never published, so the only visible signal is a bare non-zero exit. The runtime source exists in the repository checkout only under gitignored `.ai/local/vendor/gsd-path/`; verified 2026-10-27, that extracted copy computes exactly the pinned digest `6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f`, so the tracked vendored archive must be created by this task. The restore route is proven (rehearsed 2026-10-27): the installer is pure-stdlib `scripts/install.py` (no npm needed), exits 0 printing `runtime: restore 1.6.2 (6f95a31e…) (dry run)` on a matching source, and aborts with `error: source does not match declared runtime 1.6.2 (6f95a31e…); use its matching package` on a doctored source — the recorded digest pair of E1. PR-triggered runs check out a detached merge ref where the documented fail-closed branch ownership fires; the INTENT acceptance surface is the push-to-main run, so a red PR run with published diagnostics is documented honest behavior, not a defect to suppress (N3).

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
