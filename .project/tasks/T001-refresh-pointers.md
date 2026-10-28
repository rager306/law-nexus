---
id: T001
title: Refresh roadmap marker and audit queue to M003 shipped state
wave: 1
deps: []
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - prd/project-state/roadmap.md
  - prd/project-state/data/roadmap.json
  - docs/agent-stack/history/LEGACY_CROSSWALK.md
  - .project/research/DOCS-AUDIT.md
  - tests/test_project_state_roadmap_freshness.py
---

# T001 — Refresh roadmap marker and audit queue to M003 shipped state

## Context

M003 shipped with milestone ci-honesty; the roadmap and queue trail behind.

## Approach

- Update roadmap.md live marker to ci-honesty/gsd-path/M004 (shipped); update roadmap.json current_milestone.id.
- Update DOCS-AUDIT queue rows for T005/T006/T001–T011 completed work.
- Update crosswalk M225 row linking the rerun receipt.

## Interface contract

- None

## Intent coverage

- SC1
- SC2

## Acceptance criteria

1. Roadmap marker names ci-honesty on gsd-path/M004; three-way identity test passes.
2. Held-out E2: the roadmap consistency test also confirms no stale `planned: no` rows for completed M001-M003 tasks.

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py::test_native_marker_names_the_operational_milestone -q
```

## Log

- 2026-10-28 — created by plan (quick mode)
