---
id: T001
title: Land the five pre-milestone fixes on gsd-path/M001
wave: 1
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - Cargo.toml
  - src/law_nexus_harness/governor.py
  - scripts/ai/phase-dispatch.py
  - tests/test_harness_governor.py
  - tests/test_phase_dispatch_adapter.py
  - tests/test_path_isolation_recovery.py
  - .gitignore
---

# T001 — Land the five pre-milestone fixes on gsd-path/M001

## Context

Five verified fixes sit uncommitted in the primary worktree because the guard blocks product-file commits outside build; the canonical patches are preserved outside the repository under /root/law-nexus-pre-milestone-fix/. They are: the measured dev-profile rework (dev-profile-strip.patch targets Cargo.toml), the pre-milestone roadmap-freshness pass for inspect/define (pre-milestone-phase.patch targets src/law_nexus_harness/governor.py and tests/test_harness_governor.py), and the unclassified dispatch outcome plus the appended brief completion contract (unclassified-and-brief-contract.patch targets scripts/ai/phase-dispatch.py and tests/test_phase_dispatch_adapter.py). SC1 makes these the first task commits on the bound branch, and SYNTHESIS names tree-versus-patch drift as the assumption to burn before anything builds on the fixes. The 2026-10-26 handoff records the suites' baseline as 248/0 governor and 27/0 dispatcher through uv run --frozen.

## Approach

- In the isolated task tree at the recorded base, apply each canonical patch with `git apply --check` first, then apply it. If any patch does not apply cleanly, the drift SYNTHESIS warns about is real: block with NEEDS-ORCHESTRATOR instead of hand-fitting the diff.
- The landed diff must be exactly the union of the three patches plus the new E1 test file; nothing else, no re-derivation of the fixed content.
- Write tests/test_path_isolation_recovery.py to pin E1 (held-out, criterion SC1): resolve the pipeline helper by running the tracked launcher `python3 -B .gsd-path/status_runtime.py --runtime-path` against this repository root and joining the printed runtime directory with isolation.py; then, in temporary git repositories created by the test, assert the recovery contract: a detached HEAD is refused (fail-closed — no recovery outside the helper), and an interrupted or unlanded task yields an honest verdict from the helper's own verdict set rather than an invented success. Keep the test hermetic and fast; it pins the helper contract, it does not re-implement it.
- Python runs only through `uv run --frozen` (INTENT constraint); never `git stash` in this repository (standing owner rule); the orchestrator owns landing, not the coder.

## Interface contract

- None

## Intent coverage

- SC1

## Acceptance criteria

1. The three canonical patches apply cleanly to the task base with `git apply --check`, and the landed diff for the five fixed files equals their union with no other product change.
2. `uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py` — SC1's exact command — reports 0 failures as part of the Verify run below.
3. E1 is pinned by tests/test_path_isolation_recovery.py: an interrupted task landing recovers only through the pipeline isolation helper's recover command; the helper refuses a detached HEAD and reports an honest verdict for an interrupted or unlanded task, never a fabricated success; manual git repair stays vetoed.
4. The landing commit touches only declared paths. Sequencing note (orchestrator, 2026-10-26): the two-line `.gitignore` anchoring already landed with T002 (99abed61), so this task's landing touches the remaining declared paths; `.gitignore` stays a declared (expected-unchanged) path and must not be modified again.

## Verify

```bash
uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py tests/test_path_isolation_recovery.py -q
```

Heavy: no

## Log

- 2026-10-26 — orchestrator: AC4 reworded — the .gitignore anchoring landed with T002 (99abed61) before this task's redispatch; .gitignore remains declared-but-unchanged for this landing.
- 2026-10-26 — created by planner
- 2026-10-26 — NEEDS-ORCHESTRATOR: Verify cannot reach 0 failures at base 1f435a32 — the live governor's roadmap-current-tracks-path fails there (roadmap.json still names M225-qrwdfv while STATE.md says 001-native-workflow-acceptance/build), failing 12 pre-existing test_live_governor_* assertions outside this task's files; marker-sync must land before this task's Verify evidence is taken.
- 2026-10-26 — Orchestrator answer: yes — T002 (marker sync) lands first and this task's Verify evidence is taken at a base containing that landing — cited: PLAN.md Wave 1 “risk burn-down” (SYNTHESIS wave-1 blocker 3: the fail-closed governor gates every later native claim), INTENT.md SC2 and Edge coverage E2 (missing/mismatched marker is a blocking error).
- 2026-10-26 — plan-defect repair (orchestrator, per build-native step 2 and the finish preflight receipt): `files` gains `.gitignore`; AC4 reworded to seven paths with the exact two-line anchoring `/build/`, `/archive/` (legacy unanchored product rules swallow `.project/build/` and `.project/archive/`, which GSD Path state must track). Task returned to pending for redispatch at a base containing T002's landing.
- 2026-10-26 — build_T001 implementation: applied the three canonical patches
  cleanly with `git apply --check` then `git apply` (dev-profile-strip →
  Cargo.toml; pre-milestone-phase → src/law_nexus_harness/governor.py +
  tests/test_harness_governor.py; unclassified-and-brief-contract →
  scripts/ai/phase-dispatch.py + tests/test_phase_dispatch_adapter.py); the
  five-file diff is exactly the union of the patches, no re-derivation. Wrote
  tests/test_path_isolation_recovery.py pinning E1: helper resolved through the
  tracked launcher (`python3 -B .gsd-path/status_runtime.py --runtime-path`),
  detached HEAD refused fail-closed, unlanded task → `none`, interrupted task →
  `resume` at its base, every verdict held to the helper's own vocabulary and
  never a landed verdict without a landing commit.
