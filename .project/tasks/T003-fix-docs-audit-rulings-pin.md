---
id: T003
title: Fix the stale DOCS-AUDIT rulings pin in the pointer suite
wave: 2
deps: []
status: pending
agent: null
base: null
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
