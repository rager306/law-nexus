---
id: T011
title: Make the governor and preflight suites branch-environment-aware
wave: 4
deps: [T001]        # task ids whose output or landed effect this task needs — T001 landed the tests/test_harness_governor.py content this task edits
status: done
agent: build_T011
base: e85cf2b49dc3686e72789ba97fc34dec892c1103
worktree: null
task_branch: null
files:              # every file this task may touch — dispatch checks overlap
  - tests/test_harness_governor.py
  - tests/test_harness_preflight.py
---

# T011 — Make the governor and preflight suites branch-environment-aware

## Context

P001 (PATCH-FINDINGS.md) blocks ship at the reviewed commit. Finding, carried verbatim — Evidence: "Project Verify failed at the reviewed commit." Fix direction: "Resolve the recorded command failure before shipping." The orchestrator's recorded failure (non-normative note, PATCH-FINDINGS.md): 14 failed / 634 passed / 7 skipped — live-governor ×12 + preflight ×2, "all asserting `error_count == 0` on a `gsd-path-verify/*` sidecar branch where the documented fail-closed branch ownership fires; identical suite green on the bound branch (r2: 278/0; wave-gate governor 0 errors)" — "Environment contract mismatch, not a product defect." The failing tests are exactly: in tests/test_harness_governor.py the twelve `test_live_governor_*` tests that call `run_governor(ROOT)` on the live repository and assert `report.error_count == 0` / `report.status == "ok"`; in tests/test_harness_preflight.py `test_cli_preflight_command_emits_stable_json` (asserts exit code 0 and status "ok" for the live-root preflight) and `test_cargo_formatter_failure_is_fail_closed_and_actionable` (asserts `error_count == 1` with one injected cargo-fmt failure). The behavior they collide with is the documented contract, not a defect: away from the bound branch, `check_workflow_state_surface` (src/law_nexus_harness/governor.py) reports the blocking finding (`check_id="workflow-state-surface"`, severity error, rule `workflow-state-surface.blocking`) and the preflight `workflow-state-surface` check fails the same way, so error_count rises honestly (INTENT constraint: "Governor is branch-locked and fails closed away from the bound branch — by design"; PLAN.md Surface contract: away from the bound branch that error is "expected behavior, not a defect"). Owner ruling (a) for the patch round: make both modules branch-environment-aware — on the bound branch gsd-path/M001 the full assertions stay unchanged; on any non-operational branch (e.g. `gsd-path-verify/*` verify sidecars) the tests pin the fail-closed contract itself instead of asserting `error_count == 0`. This protects SC1's recorded-evidence integrity: Project Verify must pass for honest reasons in both environments, never because a check was suppressed (N3).

## Approach

- Detect the branch environment honestly at test time: read the current branch of ROOT (read-only `git rev-parse --abbrev-ref HEAD` or an equivalent existing helper) and split on exactly one predicate — bound branch `gsd-path/M001` → full-assertion path; every other branch → pinned-contract path. Do not enumerate sidecar name patterns and do not read environment variables or pytest metadata as the signal: the contract is "away from the bound branch", and a heuristic that could classify the bound branch as non-operational would make the pinned path vacuous there.
- The pinned-contract path pins the fail-closed contract itself, per module: the governor tests assert the live report carries the blocking `workflow-state-surface` finding (severity error, rule `workflow-state-surface.blocking`), `report.status == "failure"`, and honest error-count semantics (the recorded blocking errors counted, never 0); the preflight tests assert the live `workflow-state-surface` check fails blocking with the same honest counting, and `test_cargo_formatter_failure_is_fail_closed_and_actionable` keeps its injected cargo-fmt failure asserted and counted alongside the environment error. Derive counts from the report's own failed checks where possible — assert the contract, not a guessed constant.
- The bound-branch path keeps the pre-change assertions unchanged: gate the existing bodies behind the branch predicate rather than rewriting them, so the diff shows the original operational assertions intact. The two journal-gated skips (`_skip_without_pi_journal` and its two callers) keep their existing recorded-reason behavior untouched.
- No suppression (N3): no unconditional skip, xfail, or shell-truth fallback. The corpus-absent skip-visible pattern (`pytest.skip` with a loud recorded reason, visible under `-rs`) is the loudness precedent only — this fix does not skip in either environment; both branches produce real assertions.
- Landing constraint (file overlap): this task lists tests/test_harness_governor.py, a T001 file, so T001's Verify must also pass for this task to land.
- Python runs only through `uv run --frozen` (INTENT constraint); the coder performs no git mutations (the in-test branch read is read-only); landing is the orchestrator's.

## Interface contract

- None

## Intent coverage

- SC1

## Acceptance criteria

1. Both modules resolve the live branch at test time and split on exactly the bound predicate: on gsd-path/M001 every pre-change assertion of the live-surface tests is preserved unchanged; on any other branch the live-governor and preflight tests pin the fail-closed contract — the blocking workflow-state-surface error present and honest error-count semantics — and no assertion on that path asserts `error_count == 0`, live status "ok", or exit code 0.
2. No weakening where the governor is operational: no pre-change operational assertion is deleted or loosened; no test is removed; no unconditional skip, xfail, or suppression added (N3); the journal-gated skips behave exactly as before.
3. `uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py -q` passes in both environments: on a governor-operational branch (the task isolate; full-assertion path exercised, run's branch recorded in the Log) and on a non-operational branch (the orchestrator's gsd-path-verify/* verify sidecar at finish; pinned-contract path exercised).
4. T001's Verify still passes: `uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py tests/test_path_isolation_recovery.py -q` (file-overlap landing rule).
5. The landing diff touches exactly the two declared test modules.

## Verify

```bash
uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py -q
```
<!-- Branch-aware by construction: green on a governor-operational branch (full-assertion path exercised) and green in the gsd-path-verify/* verify sidecar at finish (pinned fail-closed-contract path exercised). The Log records which branch each recorded run used. -->

Heavy: no

## Log

<!-- Append-only: coder summary, blocks (`NEEDS-ORCHESTRATOR: <question> —
     readings: <candidates>` for contract ambiguity), orchestrator answers,
     review verdicts, fixes. -->
- 2026-10-27 — created by plan_patch
- 2026-10-27 — orchestrator: the r1 coder applied the dual-context implementation to both declared modules but exited
  before its in-flight Verify returned and without a Log entry; the orchestrator proceeds to the authoritative finish —
  its Verify runs in the gsd-path-verify sidecar (the non-operational context the new pins target) and is the binding evidence.

- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t011-verify): pass, exit 0; output tail:
  ```
  ........................................................................ [ 26%]
  ........................................................................ [ 53%]
  ........................................................................ [ 80%]
  .......ss..........................................                      [100%]
  265 passed, 2 skipped in 112.07s (0:01:52)
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t011-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t011-verify
  Installed 32 packages in 349ms
  ```
- 2026-10-27 — orchestrator regression Verify of T001 (sidecar gsd-path-verify/task-t011-verify): pass, exit 0; output tail:
  ```
  ........................................................................ [ 25%]
  ........................................................................ [ 51%]
  ........................................................................ [ 77%]
  .......ss.....................................................           [100%]
  276 passed, 2 skipped in 144.11s (0:02:24)
  ```
