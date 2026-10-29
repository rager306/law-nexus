---
id: T001
title: Name the pointer suites in the CI inventory and the refresh rule in AGENTS.md
wave: 1
deps: []
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - prd/migration/decommission/repository-quality-gate.json
  - tests/test_repository_quality_gate.py
  - AGENTS.md
  - tests/test_ci_runtime_restore.py
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
