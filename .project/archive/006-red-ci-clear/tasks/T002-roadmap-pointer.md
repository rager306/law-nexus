---
id: T002
title: Refresh the roadmap projection to the shipped milestone
wave: 1
deps: []
status: done
agent: build_T002
base: d276fb3dad28872984b27a4862ac52f30dbeb21b
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
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  sssss.....                                                               [100%]
  5 passed, 5 skipped in 5.17s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
  Installed 32 packages in 297ms
  ```
