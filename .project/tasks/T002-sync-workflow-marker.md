---
id: T002
title: Sync the workflow marker to the Path milestone
wave: 1
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - prd/project-state/roadmap.md
  - prd/project-state/data/roadmap.json
  - tests/test_project_state_roadmap_freshness.py
---

# T002 — Sync the workflow marker to the Path milestone

## Context

Define set the native milestone 001-native-workflow-acceptance in .project/STATE.md, but the tracked roadmap front still names the frozen Pi milestone M225-qrwdfv as active — the marker bullet near the top of prd/project-state/roadmap.md and the current_milestone block in prd/project-state/data/roadmap.json. The governor's roadmap-current-tracks-path check compares the roadmap data against the live native milestone by identity, so it fails on the bound branch until the sync lands; SYNTHESIS lists this as wave-1 blocker 3 because the branch-locked, fail-closed governor gates every later native claim. SC2 requires the marker to name this Path milestone slug exactly and the governor to report 0 errors with the milestone set. E2 makes a missing or mismatched marker a fail-closed blocking error. This is also the audit #15 ride-along named in INTENT Scope in.

## Approach

- N4 is the hard line: only the workflow-marker bullet changes in prd/project-state/roadmap.md — the bullet that begins with the words Local GSD workflow marker. The superseded 2026-10-16 marker bullet below it is historical and stays untouched; no M-number registry row, completed-milestone line, requirements status, or any other line in that file moves. The final reviewer diffs the file against exactly this rule.
- Update the current_milestone identity in prd/project-state/data/roadmap.json to id 001-native-workflow-acceptance with status active, plus its title and goal describing this Path milestone, so the governor comparison passes by identity and never by sequence-number guessing. Do not touch completed_milestone_groups, sanctioned_execution_chain, or any historical record.
- Extend tests/test_project_state_roadmap_freshness.py with a native marker test that reads the tracked .project/STATE.md milestone, the roadmap.json current_milestone.id, and the roadmap.md marker bullet, and asserts exact slug equality across all three (E2). The test reads tracked files directly so it runs in any sidecar; the legacy registry tests keep their skip behavior under operational native state.
- Record a bound-branch governor run (`uv run --frozen python -m law_nexus_harness.governor`) with 0 errors in the task Log as the SC2 evidence. A verify sidecar legitimately shows only the branch-ownership error — that is the documented fail-closed behavior — so the Verify below is sidecar-safe by design.

## Interface contract

- None

## Intent coverage

- SC2

## Acceptance criteria

1. The diff of prd/project-state/roadmap.md touches only the marker bullet (N4), and that bullet names the milestone 001-native-workflow-acceptance exactly — the full slug, not a prefix, suffix, or reworded variant (E2, fail-closed on mismatch).
2. prd/project-state/data/roadmap.json has current_milestone.id equal to 001-native-workflow-acceptance with status active; no historical row, completed group, or recorded hash changed.
3. The new native marker test asserts exact identity between the STATE.md milestone, the roadmap.json current_milestone.id, and the roadmap.md marker bullet, and does not skip when the native state is operational.
4. The task Log records a governor run on gsd-path/M001 reporting 0 errors with the milestone set and no pre-milestone exception in play.

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
```

Heavy: no

## Log

- 2026-10-26 — created by planner
