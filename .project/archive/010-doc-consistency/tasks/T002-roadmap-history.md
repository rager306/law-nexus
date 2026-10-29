---
id: T002
title: Complete the roadmap history and refresh the current-state pointer
wave: 1
deps: [T001]
status: done
agent: build_T002
base: 78203174a171c5bad034dc3561f8cf80edbcaa09
worktree: null
task_branch: null
files:
  - prd/project-state/roadmap.md
  - docs/agent-stack/POST-SHIP-STATE-2026-10-28.md
  - tests/test_project_state_roadmap_freshness.py
---

# T002 — Complete the roadmap history and refresh the current-state pointer

## Context

The live marker records the current milestone, but the superseded history skips
the M003, M004, M005, M006 and M008 shipments, so a fresh reader cannot tell
what landed. The marker also points at
`docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` as the current-state document
while that report stops before M008.

## Approach

- Add one dated superseded bullet per missing shipment, with its ship commit,
  integration merge, tag and archive.
- Extend the current-state report with the M008/M009 outcome so the pointer
  names a document that describes the shipped world.

## Interface contract

- None

## Intent coverage

- SC3
- SC4

## Acceptance criteria

1. Every archive under `.project/archive/` has a dated history bullet, and the history is appended, never deleted (E3, N2).
2. The current-state pointer names a report that describes the post-M009 world.
3. The pointer suites pass (E4, N3).

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
```

## Log

- 2026-10-29 — created by plan (quick mode)
- 2026-10-29 — orchestrator Verify (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  sssss......                                                              [100%]
  6 passed, 5 skipped in 4.89s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
  Installed 32 packages in 297ms
  ```
