---
id: T001
title: Key the live-suite expectations on STATE-phase semantics and pin the classification matrix
wave: 1
deps: []
status: done
agent: build_T001
base: 6286138fdda4a2e7a768a0c2bc6d1abd298a763a
worktree: null
task_branch: null
files:
  - tests/test_harness_governor.py
  - tests/test_harness_preflight.py
  - tests/branch_context.py
  - tests/test_branch_context.py
---

# T001 — Key the live-suite expectations on STATE-phase semantics and pin the classification matrix

## Context

M002's T003 landed the five-scenario matrix, but the SHIPPED_MAIN scenario keys on the branch name (`main`) and expects Contract A (exit 0 / 0 errors). On the integrated main CI context the checkout's STATE.md says `build/active` (M002 in flight), so the real governor honestly reports the roadmap mismatch (1 error) and 14 routed assertions fail (CI run 40533158703). Owner ruling: the expectation must key on the checkout's STATE.md phase semantics — `build/active` asserts the honest single-error roadmap finding naming the M002 continuation; `shipped/done` asserts Contract A pass; fail-closed pins (foreign/detached/sidecar) unchanged (N1). E2 (M001 T011 / M002 T003) pins the predicate; E1 keys the phase.

## Approach

- Extend `tests/branch_context.py` with a `state_phase` field on StateBinding (read from STATE.md's `status:`/`phase:` lines — `build`/`active` or `shipped`/`done`); `classify` returns the context plus the phase; SHIPPED_MAIN's expectation branches on phase: `shipped` → Contract A pass, `build` → the honest single-error roadmap finding (exit 1, error_count ≥ 1, roadmap-current-tracks-path present).
- Update the SHIPPED_MAIN-routed tests in both suites to assert per the phase; keep all other pins verbatim.
- Add `tests/test_branch_context.py::test_classification_matrix_all_contexts_both_phases` pinning the full classification matrix (held-out E2).
- Add the grep pin `test_no_milestone_literals_in_expectations` (SC2).

## Interface contract

- None

## Intent coverage

- SC1
- SC2

## Acceptance criteria

1. On gsd-path/M003 (bound, build/active): all three suites pass with the routed full assertions exercising the honest roadmap finding (exit 1 asserted where the phase semantics demand it).
2. On a gsd-path-verify/* sidecar: the fail-closed pins pass (unchanged from M002).
3. `tests/test_branch_context.py::test_classification_matrix_all_contexts_both_phases` covers five contexts × two STATE phases.
4. `test_no_milestone_literals_in_expectations` passes; `gsd-path/M0` literals appear only in fixture-payload whitelisted regions.
5. Held-out E2: `test_classification_matrix_all_contexts_both_phases` pins the classification for all five contexts × both STATE phases.

## Verify

```bash
uv run --frozen pytest tests/branch_context.py tests/test_branch_context.py tests/test_harness_governor.py tests/test_harness_preflight.py -q
```

## Log

- 2026-10-27 — created by plan (quick mode)

- 2026-10-28 — orchestrator Verify (isolate gsd-path-task/T001): fail, exit 1; output tail:
  ```
  ........................................................................ [ 24%]
  ........................................................................ [ 49%]
  ........................................................................ [ 73%]
  ...............................ss..........................F............ [ 98%]
  ....                                                                     [100%]
  =================================== FAILURES ===================================
  __________ test_cargo_formatter_failure_is_fail_closed_and_actionable __________
  
  >   ???
  E   AssertionError: assert 'trajectory-governor' in {'cargo-fmt-workspace': {'check_id': 'cargo-fmt-workspace', 'command': ['cargo', 'fmt', '--all', '--', '--check'], 'duration_ms': 2, 'exit_code': 1, ...}}
  
  tests/test_harness_preflight.py:390: AssertionError
  =========================== short test summary info ============================
  FAILED tests/test_harness_preflight.py::test_cargo_formatter_failure_is_fail_closed_and_actionable
  1 failed, 289 passed, 2 skipped in 114.22s (0:01:54)
  ```

- 2026-10-28 — build_T001 r1 implementation record: completed on the four owned files —
  `StatePhase` pairing + `Classification`/`classify_checkout` on `branch_context.py`;
  phase-keyed operational expectations in both live suites (`build/active` asserts the honest
  roadmap mismatch via `_assert_honest_roadmap_mismatch` / trajectory-governor; `shipped/done`
  asserts Contract A; fail-closed pins verbatim); the SHIPPED_MAIN surface arms branched on the
  phase and the stale `.project/archive/001-...` literal replaced by the milestone-neutral
  `outcome shipped/done; archive .project/archive/` proof shape (SC2);
  `test_classification_matrix_all_contexts_both_phases` (5 contexts x 2 phases, E2);
  `test_no_milestone_literals_in_expectations` + scanner canary (SC2/E3); the main+build/active
  fixture stack (cutover=false) pinning the honest branch-ownership block and the explicit
  roadmap `comparison=not-performed` skip (E1). Verify reached 289 passed / 2 skipped / 1 failed
  (the one failure was the cargo test wrongly expecting the live roadmap error under the faked
  governor; fixed and the three live preflight tests re-verified green at 09:46).

- 2026-10-28 — NEEDS-ORCHESTRATOR: the r1 implementation is destroyed and unrecoverable in this
  worktree — at ~09:50 the branch moved to 6286138f and a `reset: moving to HEAD` (reflog)
  reverted the four uncommitted owned files to the 878518aa state (no ref or dangling object
  holds the changes), and `refs/gsd-path/task-authorizations/T001` is absent, so the pinned
  helper routes `block` here and no in-worktree Verify can pass until re-isolation. Should T001
  be re-dispatched through a fresh `isolate-task` (recreates the authorization; the r1 approach
  and this Log are preserved at 6286138f)? — readings: (a) fresh re-dispatch, recommended: the
  implementation is fully specified by the r1 record and reproducible; (b) restore the task
  authorization ref in place and re-Verify the current tree without re-isolation.

- 2026-10-28 — build_T001 r2 (fresh re-dispatch; orchestrator preserved the r1 work at
  /root/law-nexus-pre-milestone-fix/t001-m003-work.patch): re-applied the patch with
  `git apply --include='tests/*'` onto this re-isolated worktree at 6286138f. The preserved r1
  state already carries the corrected BOUND-path assertions the r1 Verify demanded: on the
  operational context `test_cargo_formatter_failure_is_fail_closed_and_actionable` pins the
  actual report content (status=failure; the single injected `cargo-fmt-workspace` error with
  command, remediation and stderr_tail; `error_count == 1` under the faked-ok governor runner),
  while the live roadmap mismatch is asserted where the real governor runs —
  `trajectory-governor` failing with `failed_checks=['roadmap-current-tracks-path']`
  (confirmed against the real `run_preflight` output on this checkout before Verify). No
  assertion was weakened. Verify (`uv run --frozen pytest tests/branch_context.py
  tests/test_branch_context.py tests/test_harness_governor.py tests/test_harness_preflight.py -q`):
  pass — 290 passed, 2 skipped in 100.53s; r1's failing test now passes; an independent grep
  confirms no `gsd-path/M0` literal in either live suite (SC2). The r1 NEEDS-ORCHESTRATOR block
  above is resolved by this re-dispatch: the implementation is on the four owned files and ready
  for the independent orchestrator Verify.
- 2026-10-28 — orchestrator Verify (isolate gsd-path-task/T001): pass, exit 0; output tail:
  ```
  ........................................................................ [ 24%]
  ........................................................................ [ 49%]
  ........................................................................ [ 73%]
  ...............................ss....................................... [ 98%]
  ....                                                                     [100%]
  290 passed, 2 skipped in 113.17s (0:01:53)
  ```
