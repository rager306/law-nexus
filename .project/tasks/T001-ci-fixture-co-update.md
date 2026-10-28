---
id: T001
title: Derive the roadmap fixture milestone and accept both bound-branch phases
wave: 1
deps: []
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - tests/test_harness_governor.py
  - tests/test_harness_preflight.py
---

# T001 — Derive the roadmap fixture milestone and accept both bound-branch phases

## Context

CI run 40669688711 fails two live-surface tests: the roadmap fixture hardcodes a
stale native milestone, and the bound-branch pins assume build/active while a
shipped bound branch is shipped/done.

## Approach

- Derive the fixture milestone from the tracked roadmap.json at import time.
- Accept both bound-branch phases in the surface pins.

## Interface contract

- None

## Intent coverage

- SC1
- SC2

## Acceptance criteria

1. The fixture derives the milestone from roadmap.json (no literal); held-out E1 pins the loud failure on a missing id.
2. Both `build/active` and `shipped/done` are accepted on the bound branch; any other phase fails.
3. The full suite reports 0 failures on the bound branch.

## Verify

```bash
uv run --frozen pytest tests/test_harness_governor.py -q -k 'TestRoadmapFreshnessAgainstNativePath or live_workflow_state_surface'
```

## Log

- 2026-10-28 — created by plan (quick mode)
