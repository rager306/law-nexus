---
id: T002
title: Classify the shipped-integrated main state as an honest non-blocking workflow state
wave: 1
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - src/law_nexus_harness/workflow_state.py
  - src/law_nexus_harness/governor.py
  - src/law_nexus_harness/preflight.py
  - tests/test_harness_workflow_state.py
---

# T002 — Classify the shipped-integrated main state as an honest non-blocking workflow state

## Context

On integrated main the pinned helper routes `block` ("current branch main != STATE.branch gsd-path/M001") with `completion.status` `verified`, outcome `shipped/done`, and the archive proof — probed 2026-10-27 on a fresh named-branch checkout of 4e0cd4db with the restored runtime (proof: ship commit `886a36a8`, integrate/landing `4e0cd4db`, tag `milestone/001-001-native-workflow-acceptance`, archive `.project/archive/001-001-native-workflow-acceptance`). The typed adapter maps every non-operational route action to `CONFLICTING_OWNERSHIP`, a blocking error, so the governor can never exit 0 on main and SC1's shipped-main contract is unreachable. AGENTS.md's plain-prompt re-entry already treats a verified completion on an ordinary branch as normal operation; the adapter must classify that state honestly instead of blocking (SC1), while every genuinely non-operational state stays fail-closed (N2). Detached HEADs, foreign branches, and verify sidecars keep `CONFLICTING_OWNERSHIP`: their payloads carry `completion.status` `unverified` or active phases, so the narrow Contract A predicate cannot swallow them (E3's distinct expectations).

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

- SC1

## Acceptance criteria

1. `read_workflow_state` classifies the verified shipped/done `block` payload as `SHIPPED_INTEGRATED` (`"shipped-integrated"`), non-blocking with remediation `"none"`, observed naming shipped/done and the archive path; every other non-operational route (foreign branch, detached, verify sidecar, unverified or active states) stays `CONFLICTING_OWNERSHIP` with unchanged observed/remediation (N2, E3).
2. The governor check emits the `workflow-state-surface.shipped` pass finding and the preflight check emits the `state=shipped-integrated` pass per Contract A, and `workflow_readiness` returns `"operational"` for the new kind.
3. A wrongly-typed `completion` field in the payload fails closed to `invalid-schema`; an absent or null `completion` is not a shipped proof.
4. The existing conflicting-ownership, runtime-unavailable, and identity-typing tests in `tests/test_harness_workflow_state.py` pass unchanged, plus new tests pinning Contract A; the suite is green in a verify sidecar (fixture-based — no live state needed).

## Verify

```bash
uv run --frozen pytest tests/test_harness_workflow_state.py -q
```
<!-- Fails if the shipped-integrated classification, its fail-closed typing, or either
     surface branch is skipped. Fixture-based: green on the bound branch and in a
     gsd-path-verify/* sidecar alike. -->

Heavy: no

## Log

<!-- Append-only: coder summary, blocks (`NEEDS-ORCHESTRATOR: <question> —
     readings: <candidates>` for contract ambiguity), orchestrator answers,
     review verdicts, fixes. -->
- 2026-10-27 — created by planner
