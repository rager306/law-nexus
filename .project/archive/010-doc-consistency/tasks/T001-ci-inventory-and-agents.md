---
id: T001
title: Name the pointer suites in the CI inventory and the refresh rule in AGENTS.md
wave: 1
deps: []
status: done
agent: build_T001
base: f65d886191e6449744f2422c93790ed90e694640
worktree: null
task_branch: null
files:
  - prd/migration/decommission/repository-quality-gate.json
  - tests/test_repository_quality_gate.py
  - AGENTS.md
  - tests/test_ci_runtime_restore.py
  - tests/test_post_ship_pointers.py
---

# T001 — Name the pointer suites in the CI inventory and the refresh rule in AGENTS.md

## Context

M008 put `tests/test_post_ship_pointers.py` and
`tests/test_project_state_roadmap_freshness.py` in the CI process list, but the
quality-gate inventory (`repository-quality-gate.json` `ci_process_suite`) and
the pin that mirrors it still list the older set, so the inventory describes a
CI that no longer exists. Separately, the ship-time projection refresh rule
recorded in `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` is reachable only
from one sentence in `roadmap.md`; a fresh agent reading `AGENTS.md` never
learns it.

## Approach

- Add both pointer suites to the inventory and to the pin's mirror set.
- Name the refresh rule and its path in `AGENTS.md`.

## Interface contract

- None

## Intent coverage

- SC1
- SC2
- SC4

## Acceptance criteria

1. The inventory and its pin name every suite the CI process list runs (E1: dropping a pointer suite fails the pin; N1: the inventory grows to the list, never the reverse).
2. `AGENTS.md` names the ship-time refresh rule and its tracked path (E2, N4).
3. The repository-quality-gate suite passes.

## Verify

```bash
uv run --frozen pytest tests/test_repository_quality_gate.py -q
```

## Log

- 2026-10-29 — created by plan (quick mode)
- 2026-10-29 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  .....                                                                    [100%]
  5 passed in 1.59s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 1.51s
  ```
- 2026-10-29 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  .....                                                                    [100%]
  5 passed in 1.14s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 278ms
  ```
