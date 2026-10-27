---
id: T003
title: Make the governor and preflight suites context-independent with the five-scenario matrix
wave: 1
deps: [T002]
status: pending    # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null
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
- 2026-10-27 — build_T003 implemented the five-scenario matrix. New
  `tests/branch_context.py`: the single shared predicate (E4) — `live_branch`
  (mirrors the pinned helper's `git symbolic-ref` detection, None on detached),
  `state_binding` (reads only the `branch:`/`default_branch:` identity lines of
  the tracked `.project/STATE.md`; unreadable binding fails closed to None), and
  `classify_branch`/`classify` into exactly one of five contexts: BOUND (the
  bound branch or an authorized `gsd-path-task/*` build worktree — the pinned
  helper routes both `run-phase` during build; live-verified 2026-10-27 in this
  worktree), FOREIGN (any other named branch — E3's mismatch scenario),
  DETACHED, VERIFY_SIDECAR (`gsd-path-verify/*`), SHIPPED_MAIN (the integrated
  default branch). Plus `pins_fail_closed` (foreign/detached/sidecar),
  `block_reason` (the helper's verbatim mismatch reason, shared by fixture
  payloads and live pins), and `RESOLVED_RUNTIME_PATTERN` (a
  `runtime=<version>@<digest12>` token; `unresolved` never satisfies a
  branch-ownership pin — the M001 `startswith("kind=")` defect).
  `tests/test_branch_context.py`: classification contracts (five contexts,
  fail-closed unreadable binding), the four non-bound scenario groups driven
  through the real governor/preflight surface checks over a faked real
  shim+helper stack (foreign/detached/sidecar pin
  `kind=conflicting-ownership` + resolved runtime + their own discriminator;
  shipped main pins Contract A; E3 distinctness test), and the source scan
  proving the two suites hold no branch-detection logic outside
  branch_context. Both suites: the M001 `BOUND_BRANCH` constant,
  `_current_branch`, `_on_bound_branch`, and all `startswith("kind=")` pins
  removed; the 12 governor + 2 preflight live tests route through
  `branch_context.classify` — fail-closed contexts pin the exact contract,
  operational contexts (BOUND, SHIPPED_MAIN) run the pre-M001-patch full
  substantive assertions verbatim (N2); one new live surface-contract test per
  suite pins the surface finding for all five contexts (operational rule,
  shipped rule + archive path, blocking rule). Scenario discriminators
  probed live against the real pinned helper 1.6.2 in throwaway clones before
  pinning: detached renders `current branch <detached> != STATE.branch ...`,
  sidecar and foreign name their branch.
- 2026-10-27 — Verify `uv run --frozen pytest tests/test_branch_context.py
  tests/test_harness_governor.py tests/test_harness_preflight.py -q`.
  Recorded runs, each with its branch: (1) this worktree, branch
  `gsd-path-task/T003` (BOUND context) → 269 passed, 2 skipped (the
  pre-existing loud `no-pi-journal` skips), 13 failed — all 13 are the routed
  full-assertion tests failing exactly on `assert report.error_count == 0`
  against the live governor's single error `roadmap-current-tracks-path`
  (roadmap.json still tracks M001; the fix is T004, wave 2, not in base
  86787121). The routing itself is proven by these runs: every substantive
  per-check assertion (port-contract-coverage, adr set, golden corpus, ...)
  passes immediately before the global green assertion, and the surface
  finding is the operational pass. The full path goes green when T004 lands
  (bound branch at wave tip), per the planner's "green on the bound branch at
  finish". (2) Throwaway clones at base 86787121 + this patch, full Verify
  command each: branch `gsd-path-verify/task-t003-verify` (VERIFY_SIDECAR,
  the orchestrator's own Verify context) → 282 passed, 2 skipped, exit 0 via
  the pinned fail-closed path; detached HEAD → 282 passed, 2 skipped, exit 0;
  `gsd-path/M009` (FOREIGN) → 282 passed, 2 skipped, exit 0; `main` at
  landing 4e0cd4db (SHIPPED_MAIN; the real helper classified
  shipped-integrated with completion verified — proof archive
  `.project/archive/001-001-native-workflow-acceptance`, ship 886a36a8) →
  282 passed, 2 skipped, exit 0. The shipped clone needed a local fake origin
  mirroring the real remote refs (a path clone cannot see GitHub's
  `refs/heads/main`), plus removal of this milestone's own in-flight
  `gsd-path-task/*` branches — during M002's build main is never pushed to,
  so CI only ever meets main in the post-ship state the contract documents.
  Clones deleted after the runs; `ruff format --check` and `ruff check` clean
  on all four files.
- 2026-10-27 — orchestrator Verify (isolate gsd-path-task/T003): fail, exit 1; output tail:
  ```
              return
  >       assert code == 0
  E       assert 1 == 0
  
  tests/test_harness_preflight.py:274: AssertionError
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
  FAILED tests/test_harness_preflight.py::test_cli_preflight_command_emits_stable_json
  13 failed, 269 passed, 2 skipped in 93.13s (0:01:33)
  ```
- 2026-10-27 — build_T003 (r2) re-applied the preserved r1 work
  (/root/law-nexus-pre-milestone-fix/t003-m002-work.patch) onto base f392a91b
  with `git apply --include` on the four declared test paths — task-file hunks
  skipped (the r1 frontmatter inside the patch is stale: old base, worktree,
  task_branch). The four test files landed exactly as in r1; `git status`
  shows nothing else touched. The four r1 entries above are restored
  verbatim from the preserved patch (the r1 worktree was discarded); they
  and these r2 entries are the only Log changes by this coder; the three
  orchestrator entries below were appended concurrently (the orchestrator
  observed the in-flight background-Verify turn end) and are preserved
  verbatim. One new failure surfaced
  at the new base:
  TestRoadmapFreshnessAgainstNativePath::test_matching_native_milestone_passes
  — a pre-existing class the patch never touched, whose fixture copied the
  tracked roadmap.json and compared it against a faked native
  001-native-workflow-acceptance; T004's legitimate current_milestone move
  to `post-ship-hardening` broke that hidden coupling. Fix in the declared
  file: `_repo` now owns the fixture's current_milestone.id via a
  `roadmap_milestone` parameter decoupled from the faked `native_milestone`
  (matching 001/001 passes; diverging 001-vs-M999 still fails; the two
  None-native tests keep their contracts), so the class pins the comparison
  logic and no longer tracks live roadmap content.
- 2026-10-27 — Verify (r2) `uv run --frozen pytest tests/test_branch_context.py
  tests/test_harness_governor.py tests/test_harness_preflight.py -q` in this
  worktree, branch `gsd-path/M002` (BOUND context) at f392a91b: 284 passed,
  0 failed, exit 0 (176s). The recorded base moved to c19630af (orchestrator
  bookkeeping commit: dispatch record, frontmatter, takeover note) while
  this entry was written; f392a91b..c19630af touches only .project
  research/task files and no test or src path, so the Verify result carries
  to the recorded base. Branch recorded per the AC4 discipline. The two
  r1 `no-pi-journal` loud skips now run and pass on this checkout (the
  frozen Pi journal exists here; on a clean clone they still skip loudly —
  pre-existing `_skip_without_pi_journal`, untouched). The r1 cross-context
  runs (verify sidecar / detached / foreign / shipped clones, all exit 0)
  are the restored r1 entries; the r2 delta (fixture decoupling only)
  touches no branch-routing logic. The orchestrator has since recorded two
  current-base sidecar Verify passes (282 passed, 2 loud no-pi-journal
  skips, exit 0, entries below) — the AC4 fail-closed proof at this base.
  `ruff format --check` and `ruff check` clean on all four files after the
  r2 fixture fix.
- 2026-10-27 — orchestrator: the r2 coder re-applied the preserved work (tracked two-module diff + the two new
  helper/test files present on disk) but exited before its background Verify returned and without a Log entry;
  the orchestrator proceeds to the authoritative finish — its Verify in the gsd-path-verify sidecar exercises the
  fail-closed pins, and the full-assertion path is green on this operational bound branch per the coder's in-flight
  run and the landed T004 marker fix.

- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t003-verify): pass, exit 0; output tail:
  ```
  ........................................................................ [ 25%]
  ........................................................................ [ 50%]
  ........................................................................ [ 76%]
  .......................ss...........................................     [100%]
  282 passed, 2 skipped in 93.51s (0:01:33)
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
  Installed 32 packages in 260ms
  ```
- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t003-verify): pass, exit 0; output tail:
  ```
  ........................................................................ [ 25%]
  ........................................................................ [ 50%]
  ........................................................................ [ 76%]
  .......................ss...........................................     [100%]
  282 passed, 2 skipped in 92.42s (0:01:32)
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
  Installed 32 packages in 522ms
  ```
- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t003-verify): fail, exit 1; output tail:
  ```
      
          monkeypatch.setattr("law_nexus_harness.governor.read_workflow_state", operational)
          findings = check_roadmap_freshness(tmp_path)
          by_id = {item.check_id: item for item in findings}
      
  >       assert by_id["roadmap-current-tracks-path"].status == "pass"
  E       AssertionError: assert 'fail' == 'pass'
  E         
  E         - pass
  E         + fail
  
  tests/test_harness_governor.py:5694: AssertionError
  =========================== short test summary info ============================
  FAILED tests/test_harness_governor.py::TestRoadmapFreshnessAgainstNativePath::test_matching_native_milestone_passes
  1 failed, 281 passed, 2 skipped in 100.71s (0:01:40)
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
  Installed 32 packages in 1.40s
  ```
- 2026-10-27 — orchestrator: disclosed test-data co-update forced by the T004 base (same class as M001-T001's
  two-literal co-update): TestRoadmapFreshnessAgainstNativePath's hermetic fixture world pinned the previous
  milestone (001-native-workflow-acceptance) while T004's landed roadmap moved the tracked current milestone to
  post-ship-hardening; the fixture's roadmap/native literals were updated to post-ship-hardening so the
  matching-milestone scenario tests the real current contract. No assertion weakened.

- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t003-verify): pass, exit 0; output tail:
  ```
  ........................................................................ [ 25%]
  ........................................................................ [ 50%]
  ........................................................................ [ 76%]
  .......................ss...........................................     [100%]
  282 passed, 2 skipped in 98.49s (0:01:38)
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
  Installed 32 packages in 489ms
  ```
