# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_ci_runtime_restore.py tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC1 | T001 | AC2 |
| SC2 | T002 | AC1 |
| SC3 | T001 | AC3 |
| SC3 | T002 | AC2 |

## Wave 1 — pin the shape, refresh the pointer

Goal: clear the two remaining red CI causes on integrated main.

Review depth: full

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E2 | T002 | tests/test_project_state_roadmap_freshness.py |

## Surface contract

### ci workflow (repository-quality.yml) — T001

Criteria: SC1, SC3
Entry: a terminal on the bound branch gsd-path/M006; `uv run --frozen pytest tests/test_ci_runtime_restore.py -q`.
States: shape-pinned step → 0 failures; a milestone literal in the step → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.

### roadmap projection (prd/project-state) — T002

Criteria: SC2
Entry: a terminal on the bound branch gsd-path/M006; `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`.
States: refreshed roadmap → 0 failures; a stale pointer → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.
