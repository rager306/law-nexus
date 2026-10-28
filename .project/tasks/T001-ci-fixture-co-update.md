---
id: T001
title: Derive the roadmap fixture milestone and accept both bound-branch phases
wave: 1
deps: []
status: done
agent: build_T001
base: 2acc22d339f24f4494a8726143c252d95761b55a
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
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  .....                                                                    [100%]
  5 passed, 244 deselected in 4.82s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 1.03s
  ```
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  .....                                                                    [100%]
  5 passed, 244 deselected in 4.25s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 276ms
  ```
