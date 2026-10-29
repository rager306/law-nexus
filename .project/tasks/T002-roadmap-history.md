---
id: T002
title: Complete the roadmap history and refresh the current-state pointer
wave: 1
deps: [T001]
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - prd/project-state/roadmap.md
  - docs/agent-stack/POST-SHIP-STATE-2026-10-28.md
  - tests/test_post_ship_pointers.py
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
uv run --frozen pytest tests/test_post_ship_pointers.py -q
```

## Log

- 2026-10-29 — created by plan (quick mode)
