---
id: T003
title: Fix the stale DOCS-AUDIT rulings pin in the pointer suite
wave: 2
deps: []
status: done
agent: build_T003
base: 9115218232d072df81554905b83bbd22926dd4d9
worktree: null
task_branch: null
files:
  - tests/test_post_ship_pointers.py
---

# T003 — Fix the stale DOCS-AUDIT rulings pin in the pointer suite

## Context

The project verify at 4a0ceb46 failed on
`tests/test_post_ship_pointers.py::test_docs_audit_queue_rows_reference_their_closing_tasks`:
the test pins the DOCS-AUDIT `## User rulings` table to exactly rows 1-19, but the
approved M011 define flow appended owner rulings #20-#24 (recorded verbatim in
DOCS-AUDIT.md and INTENT.md `## Current state`). The test's own message states the
invariant that actually matters: the original 19 rows must be kept (never deleted) —
new rows are legal. Patch finding: `.project/review/PATCH-FINDINGS.md` P001.

## Approach

- Relax the equality pin to a superset pin: `assert set(range(1, 20)) <= set(rows)`
  (all original rows present; new rows allowed). Keep the rows[6]/rows[9]/rows[19]
  content assertions unchanged — they still hold.
- Change nothing else in the file; the other pointer tests pass.

## Interface contract

None

## Intent coverage

- None

## Acceptance criteria

1. `tests/test_post_ship_pointers.py::test_docs_audit_queue_rows_reference_their_closing_tasks` passes against the current DOCS-AUDIT.md (rulings 1-19 present, 20-24 accepted).
2. The full pointer suite stays green: `uv run --frozen pytest tests/test_post_ship_pointers.py -q` reports 0 failures.

## Verify

```bash
uv run --frozen pytest tests/test_post_ship_pointers.py -q
```

Heavy: no

## Log

- 2026-10-31 — created by orchestrator (patch mode, P001)
- 2026-10-31 — implementation: relaxed the rulings pin in
  `test_docs_audit_queue_rows_reference_their_closing_tasks` from equality
  (`set(rows) == set(range(1, 20))`) to a superset pin
  (`set(range(1, 20)) <= set(rows)`); rows[6]/rows[9]/rows[19] content
  assertions kept unchanged. No other change in the file.
- 2026-10-31 — Verify: `uv run --frozen pytest tests/test_post_ship_pointers.py -q`
  → 8 passed, 0 failed (before the edit: the pinned test failed with extra
  rows 20–24, reproducing P001). Preflight at base 9115218 passed;
  DOCS-AUDIT.md carries rulings 1–24 with 6/9/19 content intact.
- 2026-10-31 — result: ready
- 2026-10-31 — orchestrator Verify (sidecar gsd-path-verify/task-t003-verify): pass, exit 0; output tail:
  ```
  ........                                                                 [100%]
  8 passed in 2.91s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/law-nexus-path-worktrees/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
        Built law-nexus @ file:///root/law-nexus-path-worktrees/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
  Installed 32 packages in 4.10s
  ```
