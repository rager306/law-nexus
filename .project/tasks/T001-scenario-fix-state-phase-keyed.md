---
id: T001
title: Key the live-suite expectations on STATE-phase semantics and pin the classification matrix
wave: 1
deps: []
status: pending     # orchestrator-owned
agent: null
base: null
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
