# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC2 |
| SC3 | T001 | AC3 |

## Wave 1 — refresh the projection at ship

Goal: keep the M008 CI guard green by naming the shipping milestone.

Review depth: full

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E1 | T001 | tests/test_project_state_roadmap_freshness.py |

## Surface contract

### roadmap projection (prd/project-state) — T001

Criteria: SC1, SC2, SC3
Entry: a terminal on the bound branch gsd-path/M009; `uv run --frozen pytest tests/test_post_ship_pointers.py -q`.
States: projection names the shipping milestone → 0 failures; a stale projection → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.
