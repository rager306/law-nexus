---
id: T001
title: Land the five pre-milestone fixes on gsd-path/M001
wave: 1
deps: []
status: pending    
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null
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

1. The three canonical patches apply cleanly to the task base with `git apply --check`, and the landed diff for the five fixed files equals their union plus the repository's `ruff format` normalization (the pre-commit hook enforces it; formatting changes only whitespace/line-shapes, never semantics — recorded by the r1 attempt). No other product change.
2. `uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py` — SC1's exact command — reports 0 failures as part of the Verify run below.
3. E1 is pinned by tests/test_path_isolation_recovery.py: an interrupted task landing recovers only through the pipeline isolation helper's recover command; the helper refuses a detached HEAD and reports an honest verdict for an interrupted or unlanded task, never a fabricated success; manual git repair stays vetoed.
4. The landing commit touches only declared paths. Sequencing note (orchestrator, 2026-10-26): the two-line `.gitignore` anchoring already landed with T002 (99abed61), so this task's landing touches the remaining declared paths; `.gitignore` stays a declared (expected-unchanged) path and must not be modified again.

## Verify

```bash
uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py tests/test_path_isolation_recovery.py -q
```

Heavy: no

## Log

- 2026-10-26 — orchestrator: first landing attempt rejected by the pre-commit ruff-format hook on src/law_nexus_harness/governor.py and tests/test_path_isolation_recovery.py (the canonical patches predate formatter normalization); AC1 amended to include the formatter normalization — semantics unchanged. Clean retry with the r1 work preserved at /root/law-nexus-pre-milestone-fix/t001-r1-work.patch.
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

- 2026-10-26 — build_T001 (redispatch at base 52f11611): re-applied the three
  canonical patches cleanly with `git apply --check` then `git apply`; the
  five-file diff is byte-identical to the patch union (verified per file).
  Restored the predecessor's E1 draft verbatim into
  tests/test_path_isolation_recovery.py after checking every assumption it
  makes against the live helper at the launcher-resolved runtime
  (6f95a31e…): `recover --repo` CLI with `.project/tasks` default resolved
  against primary, JSON report `{verdict, tasks}`, docstring verdict set
  {recovered, resume, reconcile, block, none}, `LANDED_VERDICTS =
  {recovered, attested}`, detached-HEAD refusal via `require_attached`
  ("HEAD is detached", exit 1), `none` reason "pending task has no retained
  isolate", and `resume` with `base`/`task_branch` for a retained branch at
  its base. No correction was needed.
- 2026-10-26 — build_T001 deviation from "diff = patch union + E1 file":
  updated two literals in
  TestRoadmapFreshnessAgainstNativePath::test_matching_native_milestone_passes
  (tests/test_harness_governor.py, a declared file): `_repo(tmp_path,
  "M225-qrwdfv")` and `native_milestone="M225-qrwdfv"` →
  `001-native-workflow-acceptance`. Cause: the test copies the live repo's
  `prd/project-state` into its synthetic repo, and T002's marker-sync
  (99abed61) changed `prd/project-state/data/roadmap.json` to name
  `001-native-workflow-acceptance`; the governor's identity comparison
  (current_id == native_milestone) could no longer pass with the stale
  literal — the exact test passed at the predecessor base 1f435a32 only
  because the data still named M225-qrwdfv. The two-literal update restores
  the test's documented contract (tracked roadmap data and native state name
  the same milestone) without weakening any assertion; both literals occur
  nowhere else in the file. Flagged for the orchestrator's landing review
  because the Approach pins the landed diff to the patch union plus the E1
  file.
- 2026-10-26 — build_T001 Verify: `uv run --frozen pytest
  tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py
  tests/test_path_isolation_recovery.py -q` → exit 0, 276 passed, 2 skipped
  (pre-existing skips), 0 failed. `.gitignore` untouched (declared,
  expected-unchanged). No git staging/commit/stash performed; landing is the
  orchestrator's.
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T001): pass, exit 0; output tail:
  ```
  ........................................................................ [ 25%]
  ........................................................................ [ 51%]
  ........................................................................ [ 77%]
  .......ss.....................................................           [100%]
  276 passed, 2 skipped in 88.61s (0:01:28)
  ```
- 2026-10-26 — build_T001 (r2 redispatch at base c16e11fe): the working tree
  was clean (r1 work rolled back after the hook rejection), so rebuilt from
  the preserved evidence. Applied the three canonical patches cleanly with
  `git apply --check` then `git apply` (dev-profile-strip → Cargo.toml;
  pre-milestone-phase → governor.py + test_harness_governor.py;
  unclassified-and-brief-contract → phase-dispatch.py +
  test_phase_dispatch_adapter.py) — AC1's clean-apply clause re-proven at
  this base. Re-applied the r1 two-literal update in
  TestRoadmapFreshnessAgainstNativePath::test_matching_native_milestone_passes
  (M225-qrwdfv → 001-native-workflow-acceptance) by extracting the same hunk
  verbatim from t001-r1-work.patch and applying it with `git apply` — still
  required because T002's marker landing is in this base and the test copies
  the live roadmap.json. Restored tests/test_path_isolation_recovery.py
  verbatim from /root/law-nexus-pre-milestone-fix/e1-draft/. Ran
  `uv run --frozen ruff format` on src/law_nexus_harness/governor.py and
  tests/test_path_isolation_recovery.py (AC1 formatter normalization; a
  `ruff format --check` over all five declared Python files found exactly
  those two not format-clean). Verify: `uv run --frozen pytest
  tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py
  tests/test_path_isolation_recovery.py -q` → exit 0, 278 passed, 0 skipped,
  0 failed. Delta vs r1's 276 passed, 2 skipped: the collected test set is
  identical (no test changes between 52f11611 and c16e11fe); r1's two
  pre-existing skips are the runtime-conditional no-pi-journal skips
  (pytest.skip gated on .gsd/journal/, 93 entries present at this root), so
  both ran and passed here instead of skipping. .gitignore untouched
  (declared, expected-unchanged). No git staging/commit/stash performed;
  landing is the orchestrator's.

- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): fail, exit 1; output tail:
  ```
  tests/test_harness_governor.py:2888: AssertionError
  =========================== short test summary info ============================
  FAILED tests/test_harness_governor.py::test_live_governor_includes_port_contract_coverage_finding
  FAILED tests/test_harness_governor.py::test_live_governor_passes_hostile_negative_suite_coverage
  FAILED tests/test_harness_governor.py::test_live_governor_passes_multi_adapter_port_coverage
  FAILED tests/test_harness_governor.py::test_live_governor_passes_live_adapter_readiness
  FAILED tests/test_harness_governor.py::test_live_governor_passes_ci_quality_gate_drift
  FAILED tests/test_harness_governor.py::test_live_governor_passes_verify_test_coverage_drift
  FAILED tests/test_harness_governor.py::test_live_governor_passes_semantic_stub_in_product_code
  FAILED tests/test_harness_governor.py::test_live_governor_passes_semantic_name_collision
  FAILED tests/test_harness_governor.py::test_live_governor_passes_companion_manifest
  FAILED tests/test_harness_governor.py::test_live_governor_passes_golden_corpus_catalog
  FAILED tests/test_harness_governor.py::test_live_governor_reports_historical_test_debt_visibility
  FAILED tests/test_harness_governor.py::test_live_governor_includes_adr_and_archive_checks
  12 failed, 264 passed, 2 skipped in 89.98s (0:01:29)
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 315ms
  ```
- 2026-10-26 — orchestrator: finish attempt 2 blocked in the authoritative Verify — the serial verify sidecar runs on a `gsd-path-verify/*` branch where the governor's fail-closed branch ownership fires (documented environment sensitivity; worktree probe confirmed), and the live-governor tests assert error_count==0. The identical Verify passes in the primary (gsd-path/M001) and in `gsd-path-task/*` isolates (278 passed / 0 failed, r2). Clean retry as a parallel isolate so the authoritative Verify runs where the governor is operational; the verified r2 work diff is preserved verbatim at /root/law-nexus-pre-milestone-fix/t001-r2-work.patch.
- 2026-10-26 — build_T001 (r3 redispatch at base d00219bd): restored the
  verified r2 work. `git apply --check` then `git apply` of
  t001-r2-work.patch filtered to the five declared files (Cargo.toml;
  governor.py; phase-dispatch.py; test_harness_governor.py;
  test_phase_dispatch_adapter.py) applied cleanly at this base, and a
  `git apply --reverse --check` proves the landed diff equals the patch
  hunks byte-for-byte. Brief-map deviation, resolved by the brief's own
  fallback: the r2 patch contains no tests/test_path_isolation_recovery.py
  new-file hunk (its diff headers list exactly the five files plus the task
  file, whose hunks were excluded by the include filter), so the E1 file was
  restored verbatim from /root/law-nexus-pre-milestone-fix/e1-draft/. The
  formatter check was not a no-op for that file (the e1-draft copy predates
  r2's formatting run, which survives only in the primary's tree that this
  isolate must not touch); per the brief's instruction the formatting was
  kept — line-joins only, no semantics; all five declared Python files plus
  the new file are now `ruff format --check` clean. Verify: `uv run --frozen
  pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py
  tests/test_path_isolation_recovery.py -q` → exit 0, 276 passed, 2 skipped,
  0 failed, 95.84s. Delta vs r2's 278 passed / 0 skipped: the two
  runtime-conditional no-pi-journal skips
  (test_live_governor_reports_journal_retry_loops,
  test_live_governor_reports_compat_marker_hygiene) gated on .gsd/journal/,
  which is gitignored and absent in this isolate (r2's root happened to
  carry the frozen snapshot); collected test set identical, and the SC1
  contract is 0 failures. .gitignore untouched (declared,
  expected-unchanged per AC4). No git staging/commit/stash performed;
  landing is the orchestrator's.
- 2026-10-26 — orchestrator: r3 coder applied the preserved work (tracked five verified byte-identical to the r2 diff; E1 test present with a 6-line coder adaptation of the preserved draft) but exited before its background Verify returned and without a Log entry; the orchestrator proceeds to the authoritative finish, whose Verify in the gsd-path-task isolate is the binding evidence.

