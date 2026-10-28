---
id: T002
title: Refresh the roadmap projection to the shipped milestone
wave: 1
deps: []
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - prd/project-state/data/roadmap.json
  - prd/project-state/roadmap.md
  - tests/test_post_ship_pointers.py
  - tests/test_project_state_roadmap_freshness.py
---

# T002 — Refresh the roadmap projection to the shipped milestone

## Context

On integrated main 50386e26 the projection still names `ci-fixture-fix` while
shipped STATE.md names `ci-proof-inputs`, so both pointer suites fail.

## Approach

- Set `current_milestone` to the shipped milestone with status `active`.
- Rewrite the live marker bullet to name the same slug and the M007 shipment.
- Keep the previous bullet's history as a dated superseded record.

## Interface contract

- None

## Intent coverage

- SC2
- SC3

## Acceptance criteria

1. The projection names the shipped STATE.md milestone in both roadmap.json and the live marker (E2 loud failure on an absent id).
2. No test is edited to accept the stale projection (N2, N3).

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
```

## Log

- 2026-10-28 — created by plan (quick mode)
