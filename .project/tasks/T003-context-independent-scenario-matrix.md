---
id: T003
title: Make the governor and preflight suites context-independent with the five-scenario matrix
wave: 1
deps: [T002]
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - tests/test_harness_governor.py
  - tests/test_harness_preflight.py
  - tests/branch_context.py
  - tests/test_branch_context.py
---

# T003 — Make the governor and preflight suites context-independent with the five-scenario matrix

## Context

M001's patch wave (commit 069c2ba8) made the two live suites branch-environment-aware with `BOUND_BRANCH = "gsd-path/M001"` and a broad `observed.startswith("kind=")` fail-closed expectation. The owner ruled during M001 that the fail-closed semantics were right but the pin was wrong: the broad `startswith` is satisfied even by `runtime-unavailable`, and on every branch except the pinned one the suites assert failure even where the governor is operational. Verified live on the bound branch `gsd-path/M002` (2026-10-27): `tests/test_harness_preflight.py` fails `test_cli_preflight_command_emits_stable_json` and `test_cargo_formatter_failure_is_fail_closed_and_actionable` because `_on_bound_branch()` is False while `.project/STATE.md` binds `gsd-path/M002`; twelve `if not _on_bound_branch():` guards in `tests/test_harness_governor.py` carry the same defect. The owner ruling (a): keep the fail-closed pinning semantics, add the scenario matrix (active milestone on its bound branch / foreign branch / detached / verify sidecar / shipped integrated main), and restore the substantive assertions wherever the governor is operational. CI runs both suites in `rust-harness-quality` and `migration-layer-quality`, so this matrix is also what lets main go green (shipped scenario, via Contract A) while PR merge refs stay honestly pinned (detached scenario).

## Approach

Contract constraints (the binding shapes are in Interface contract):

- `WorkflowStateKind.SHIPPED_INTEGRATED` — `law_nexus_harness.workflow_state.WorkflowStateKind` member with value `"shipped-integrated"`.
- Classification (`read_workflow_state`): when the native status payload has `route.action == "block"` AND `completion.status == "verified"` AND `state.phase == "shipped"` AND `state.status == "done"`, the report kind is `SHIPPED_INTEGRATED` (non-blocking; remediation `"none"`); `report.observed` names the shipped/done outcome and the payload's `state.archive` path. Every other non-operational route stays `CONFLICTING_OWNERSHIP`. A present-but-wrongly-typed `completion` field fails closed to `invalid-schema` (same discipline as the four existing identity sites).
- `workflow_readiness(SHIPPED_INTEGRATED)` returns `"operational"`.
- Governor finding (`check_workflow_state_surface`): `check_id "workflow-state-surface"`, `status "pass"`, `severity "ok"`, `rule_id "workflow-state-surface.shipped"`, `observed` starts with `"kind=shipped-integrated;"` and contains the archive path (`.project/archive/001-001-native-workflow-acceptance` on integrated M001 main).
- Preflight check (`_workflow_state_surface_check`): `check_id "workflow-state-surface"`, `status "pass"`, `observed` contains `"state=shipped-integrated"` and the archive path.

## Interface contract

- `WorkflowStateKind.SHIPPED_INTEGRATED` — `law_nexus_harness.workflow_state.WorkflowStateKind` member with value `"shipped-integrated"`.
- Classification (`read_workflow_state`): when the native status payload has `route.action == "block"` AND `completion.status == "verified"` AND `state.phase == "shipped"` AND `state.status == "done"`, the report kind is `SHIPPED_INTEGRATED` (non-blocking; remediation `"none"`); `report.observed` names the shipped/done outcome and the payload's `state.archive` path. Every other non-operational route stays `CONFLICTING_OWNERSHIP`. A present-but-wrongly-typed `completion` field fails closed to `invalid-schema` (same discipline as the four existing identity sites).
- `workflow_readiness(SHIPPED_INTEGRATED)` returns `"operational"`.
- Governor finding (`check_workflow_state_surface`): `check_id "workflow-state-surface"`, `status "pass"`, `severity "ok"`, `rule_id "workflow-state-surface.shipped"`, `observed` starts with `"kind=shipped-integrated;"` and contains the archive path (`.project/archive/001-001-native-workflow-acceptance` on integrated M001 main).
- Preflight check (`_workflow_state_surface_check`): `check_id "workflow-state-surface"`, `status "pass"`, `observed` contains `"state=shipped-integrated"` and the archive path.

## Intent coverage

- SC2

## Acceptance criteria

1. `tests/branch_context.py` is the single shared predicate classifying the checkout into exactly one of the five contexts, and `tests/test_branch_context.py` pins the classification plus the source-scan proving the two suites hold no other branch-detection logic (E4).
2. Five scenario groups pin their contracts as separate test scenarios: bound → full substantive assertions; foreign/detached/sidecar → fail-closed pins of `kind=conflicting-ownership` with the runtime resolved and the scenario's own discriminator; shipped-main → exit 0, `kind=shipped-integrated;`, archive path (Contract A). A foreign bound branch and a shipped main are distinct expectations, never collapsed (E3).
3. Substantive product assertions run in every context where the governor is operational: on `gsd-path/M002` the suites run the full-assertion path and pass; no assertion is weakened relative to the pre-M001-patch contracts (N2).
4. Nothing is skipped or suppressed without a loud recorded reason; the suites contain no `startswith("kind=")`-style broad pinning (N3), and both suites pass in a `gsd-path-verify/*` sidecar via the pinned fail-closed path (recorded in the Log with the branch each run used).

## Verify

```bash
uv run --frozen pytest tests/test_branch_context.py tests/test_harness_governor.py tests/test_harness_preflight.py -q
```
<!-- Context-independent by construction: green on the bound branch gsd-path/M002
     (full-assertion path) and green in the gsd-path-verify/* verify sidecar at
     finish (pinned fail-closed path). The Log records which branch each recorded
     run used. Fails if the matrix, the predicate, or any scenario contract is
     skipped or weakened. -->

Heavy: no

## Log

<!-- Append-only: coder summary, blocks (`NEEDS-ORCHESTRATOR: <question> —
     readings: <candidates>` for contract ambiguity), orchestrator answers,
     review verdicts, fixes. -->
- 2026-10-27 — created by planner
