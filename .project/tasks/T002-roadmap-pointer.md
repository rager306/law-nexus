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
  - tests/test_project_state_roadmap_freshness.py
  - tests/test_post_ship_pointers.py
---

# T002 — Refresh the roadmap projection to the shipped milestone

## Context

`prd/project-state/data/roadmap.json` names `pointer-refresh-m003` while shipped
STATE.md names the current milestone, so the roadmap-freshness suites fail on
integrated main.

## Approach

- Set `current_milestone` to the shipped milestone with status `active`.
- Keep roadmap.md's milestone line consistent with the JSON.

## Interface contract

- None

## Intent coverage

- SC2
- SC3

## Acceptance criteria

1. The roadmap projection names the shipped STATE.md milestone (N4).
2. A roadmap with an absent/empty `current_milestone.id` fails the freshness test loudly (E2).

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
```

## Log

- 2026-10-28 — created by plan (quick mode)
