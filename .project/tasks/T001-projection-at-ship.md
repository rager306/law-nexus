---
id: T001
title: Record the ship-time projection refresh and name the shipping milestone
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
  - .project/WORKFLOW-NOTES.md
  - tests/test_post_ship_pointers.py
  - tests/test_project_state_roadmap_freshness.py
---

# T001 — Record the ship-time projection refresh and name the shipping milestone

## Context

M008 added the pointer suites to CI, and run 40715983380 failed exactly there:
`roadmap.json current_milestone.id 'ci-proof-inputs' != shipped STATE.md
milestone 'pointer-in-ci'`. The projection is refreshed during build, while the
milestone is still in flight, so the following ship always lands it one
milestone behind.

## Approach

- Name the shipping milestone in `roadmap.json` and the live marker bullet, and
  keep the previous shipment as a dated superseded record.
- Record the rule — refresh the projection in a `docs:` commit immediately
  before the `.project`-only ship commit — in a tracked file the next ship reads.

## Interface contract

- None

## Intent coverage

- SC1
- SC2
- SC3

## Acceptance criteria

1. The projection names the milestone being shipped (E1: naming the previous one fails the pointer suites).
2. The refresh rule lives in a tracked file and is pinned (E2, N2).
3. The pointer suites pass on the bound branch and on the shipped tree (E3, N3).

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
```

## Log

- 2026-10-28 — created by plan (quick mode)
