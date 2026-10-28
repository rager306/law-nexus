# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_ci_runtime_restore.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T002 | AC1 |
| SC3 | T001 | AC2 |
| SC3 | T002 | AC2 |

## Wave 1 — put the pointer suites in CI

Goal: make a stale projection fail CI instead of reaching main.

Review depth: full

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E1 | T001 | tests/test_ci_runtime_restore.py |

## Surface contract

### ci workflow (repository-quality.yml) — T001

Criteria: SC1
Entry: a terminal on the bound branch gsd-path/M008; `uv run --frozen pytest tests/test_ci_runtime_restore.py -q`.
States: both pointer suites listed → 0 failures; a dropped suite → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.

### roadmap projection (prd/project-state) — T002

Criteria: SC2, SC3
Entry: a terminal on the bound branch gsd-path/M008; `uv run --frozen pytest tests/test_post_ship_pointers.py -q`.
States: projection names the shipped milestone → 0 failures; a stale pointer → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.
