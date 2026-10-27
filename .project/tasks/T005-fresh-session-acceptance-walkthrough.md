---
id: T005
title: Run the M002 acceptance walkthrough as a fresh session and record the proof on disk
wave: 2
deps: [T001, T004]
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - .project/build/M002-ACCEPTANCE-PROOF.md
---

# T005 — Run the M002 acceptance walkthrough as a fresh session and record the proof on disk

## Context

SC5's acceptance is the M001 resume discipline carried past ship: a fresh session, given only the repository and a minimal pointer, must bootstrap from disk alone and leave its verification output on disk — chat history is not proof (N5; M001 precedent: `.project/archive/001-001-native-workflow-acceptance/build/M001-RESUME-PROOF.md`, four commands recorded verbatim with exit statuses). The M002 walkthrough proves the post-ship handoff end to end: the documented bootstrap restores/verifies the pinned runtime from the vendored archive (T001's Contract B; idempotent reuse is the E2 expectation on this machine), then status/governor/freshness recognize the shipped M001 and the M002 continuation (T004's roadmap/report updates are what the status output names). The worker session reads only the pointer (Contract D's "Fresh-session bootstrap") plus the repository — no conversation context.

## Approach

Contract constraints (the binding shapes are in Interface contract):

- Vendored archive: `.ai/vendor/gsd-path-1.6.2.tgz` — a tar.gz whose single top-level directory `gsd-path/` contains `package.json` and `scripts/` of the pinned 1.6.2 GSD Path release; its content digest-matches `.gsd-path/runtime.json` (`{"version": "1.6.2", "digest": "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"}`).
- Restore procedure (the documented bootstrap command): `tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C <temporary-dir>` then `python3 <temporary-dir>/gsd-path/scripts/install.py --runtime-restore --project <repo-root> --source-root <temporary-dir>/gsd-path`. Exit 0 = the pinned runtime is installed or reused idempotently; non-zero = loud failure carrying the recorded version+digest pair. The extraction target is always a temporary directory, never a tracked path.
- Diagnostics: when the migration job's governor step fails, it publishes a workflow artifact named `governor-diagnostics` containing `governor.json` and prints the report JSON to the job log; the job exit stays non-zero. A passing run publishes no artifact.
- Shipped-main CI assertion: on a push-to-main run the governor step requires governor exit 0 and its report's `workflow-state-surface` observed to contain `"kind=shipped-integrated;"` and `".project/archive/001-001-native-workflow-acceptance"`.

- Post-ship report: `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md`, dated 2026-10-27, stating it supersedes `docs/agent-stack/CUTOVER-READINESS-M001.md` as the current-state document (that file remains untouched as the dated pre-ship snapshot).
- Fresh-session bootstrap section: headed `Fresh-session bootstrap`, listing exactly, in order: (1) the restore procedure above (vendored archive extraction + the installer's `--runtime-restore`); (2) `python3 scripts/ai/path-run.py status`; (3) `uv run --frozen python -m law_nexus_harness.governor`; (4) `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`; and the instruction to record every command with its real output at the proof file `M002-ACCEPTANCE-PROOF.md` in the pipeline `.project/build/` workspace.

## Interface contract

- Vendored archive: `.ai/vendor/gsd-path-1.6.2.tgz` — a tar.gz whose single top-level directory `gsd-path/` contains `package.json` and `scripts/` of the pinned 1.6.2 GSD Path release; its content digest-matches `.gsd-path/runtime.json` (`{"version": "1.6.2", "digest": "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"}`).
- Restore procedure (the documented bootstrap command): `tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C <temporary-dir>` then `python3 <temporary-dir>/gsd-path/scripts/install.py --runtime-restore --project <repo-root> --source-root <temporary-dir>/gsd-path`. Exit 0 = the pinned runtime is installed or reused idempotently; non-zero = loud failure carrying the recorded version+digest pair. The extraction target is always a temporary directory, never a tracked path.
- Diagnostics: when the migration job's governor step fails, it publishes a workflow artifact named `governor-diagnostics` containing `governor.json` and prints the report JSON to the job log; the job exit stays non-zero. A passing run publishes no artifact.
- Shipped-main CI assertion: on a push-to-main run the governor step requires governor exit 0 and its report's `workflow-state-surface` observed to contain `"kind=shipped-integrated;"` and `".project/archive/001-001-native-workflow-acceptance"`.

- Post-ship report: `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md`, dated 2026-10-27, stating it supersedes `docs/agent-stack/CUTOVER-READINESS-M001.md` as the current-state document (that file remains untouched as the dated pre-ship snapshot).
- Fresh-session bootstrap section: headed `Fresh-session bootstrap`, listing exactly, in order: (1) the restore procedure above (vendored archive extraction + the installer's `--runtime-restore`); (2) `python3 scripts/ai/path-run.py status`; (3) `uv run --frozen python -m law_nexus_harness.governor`; (4) `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`; and the instruction to record every command with its real output at the proof file `M002-ACCEPTANCE-PROOF.md` in the pipeline `.project/build/` workspace.

## Intent coverage

- SC5

## Acceptance criteria

1. `.project/build/M002-ACCEPTANCE-PROOF.md` exists and records, from a fresh session with no chat history, the documented bootstrap's restore step (exit 0; the already-valid store reused untouched — E2 idempotency noted) and the three verification commands with their real outputs (N5).
2. The recorded status output names branch `gsd-path/M002`, milestone `post-ship-hardening`, and the shipped/archived M001 (ship `886a36a8`, integration `4e0cd4db`); the governor exits 0; the freshness pytest passes; the proof's result block lists every exit status.
3. Any bootstrap ambiguity or failing command is recorded verbatim in the proof and blocks the task instead of being improvised or smoothed over (E7).

## Verify

```bash
test -s .project/build/M002-ACCEPTANCE-PROOF.md && grep -q "path-run.py status" .project/build/M002-ACCEPTANCE-PROOF.md && grep -q "law_nexus_harness.governor" .project/build/M002-ACCEPTANCE-PROOF.md && grep -q "post-ship-hardening" .project/build/M002-ACCEPTANCE-PROOF.md && grep -q "runtime-restore" .project/build/M002-ACCEPTANCE-PROOF.md
```
<!-- Fails when the walkthrough did not happen or the proof does not record the
     bootstrap restore and the three verification commands. -->

Heavy: no

## Log

<!-- Append-only: coder summary, blocks (`NEEDS-ORCHESTRATOR: <question> —
     readings: <candidates>` for contract ambiguity), orchestrator answers,
     review verdicts, fixes. -->
- 2026-10-27 — created by planner
