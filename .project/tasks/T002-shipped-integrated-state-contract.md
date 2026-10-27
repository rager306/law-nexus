---
id: T002
title: Classify the shipped-integrated main state as an honest non-blocking workflow state
wave: 1
deps: []
status: in-progress
agent: build_T002
base: cc9457c71619cc62eae2bd4275d0e8367101965f
worktree: /root/law-nexus
task_branch: null
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
- 2026-10-27 — build_T002 implemented Contract A. workflow_state.py: added
  `WorkflowStateKind.SHIPPED_INTEGRATED` ("shipped-integrated");
  `_native_status_verdict` now validates `state.status`, `state.archive`, and
  `completion` (object when present; string `completion.status`) eagerly beside
  the four identity sites; `read_workflow_state` classifies `block` +
  `completion.status==verified` + `state.phase==shipped` + `state.status==done`
  as SHIPPED_INTEGRATED (non-blocking, remediation "none", observed naming
  shipped/done and the payload `state.archive`); every other non-operational
  route stays CONFLICTING_OWNERSHIP; absent/null `completion` is not shipped
  proof; `workflow_readiness(SHIPPED_INTEGRATED)` = "operational".
  governor.py `check_workflow_state_surface`: pass/ok finding with rule_id
  `workflow-state-surface.shipped`, observed starts `kind=shipped-integrated;`
  and carries the archive path. preflight.py `_workflow_state_surface_check`:
  pass with `state=shipped-integrated` + archive path.
  tests/test_harness_workflow_state.py: 8 new Contract A tests
  (classification, per-condition predicate flips, no current identity on the
  shipped report, wrong-typed `completion`/`state.status`/`state.archive` fail
  closed, absent/null completion, governor + preflight pins through a faked
  shim+helper stack) and the `NATIVE_STATUS_SHIPPED_MAIN` fixture built from
  the recorded M001 proof (ship 886a36a8f9ed77ad315f4b16fee0cdbc68bf4d02,
  landing 4e0cd4dba087b3a0dfaacb4cc6a443f1bc5d495f, tag
  milestone/001-001-native-workflow-acceptance). Updated
  `test_state_unverified_kind_maps_to_blocked_readiness` — a readiness-mapping
  test outside acceptance 4's protected trio (conflicting-ownership,
  runtime-unavailable, identity-typing) — because the operational set now
  holds both kinds; leaving it unchanged would contradict the same criterion's
  "the suite is green". No protected test was modified.
- 2026-10-27 — Verify `uv run --frozen pytest
  tests/test_harness_workflow_state.py -q` → 48 passed (branch gsd-path/M002
  @ cc9457c7; fixture-based, no live state needed; `ruff check` and
  `ruff format --check` clean on all four files). Live cross-check outside the
  suite, on throwaway clones (deleted after the run): the real pinned helper
  1.6.2 against a shipped-main checkout returned exactly the fixture's shape
  (block `current branch main != STATE.branch gsd-path/M001`, completion
  verified with the same proof fields), classified shipped-integrated through
  the real shim+helper stack (governor pass `workflow-state-surface.shipped`,
  preflight pass with the archive path), while a detached HEAD at the landing
  commit (completion unverified) and a gsd-path-verify/* sidecar (not-shipped,
  build/active) both stayed CONFLICTING_OWNERSHIP — matching the Context's
  fail-closed claim for E3.
- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  ................................................                         [100%]
  48 passed in 2.43s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
  Installed 32 packages in 342ms
  ```
- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  ................................................                         [100%]
  48 passed in 2.34s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
  Installed 32 packages in 354ms
  ```
