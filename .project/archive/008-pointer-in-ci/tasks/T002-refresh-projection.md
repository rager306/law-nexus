---
id: T002
title: Refresh the roadmap projection to the shipped milestone
wave: 1
deps: []
status: done
agent: build_T002
base: bb7c5a011803fbfac0a3fb343ebe64d488b2cf2f
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
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  sssss.....                                                               [100%]
  5 passed, 5 skipped in 4.98s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
  Installed 32 packages in 301ms
  ```
