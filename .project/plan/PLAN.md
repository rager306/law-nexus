# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC2 |
| SC3 | T001 | AC3 |

## Config

- max_review_cycles: 3
- wave_budget: none
- review_panel: off
- finding_skeptics: off

## Wave 1 — refresh the projection at ship

Goal: keep the M008 CI guard green by naming the shipping milestone.

Review depth: full

## Wave 2 — fix the wave 1 review findings

Goal: move the refresh rule out of the ship gate's path, make its pin read
every prescribed step, and restore the dated M007 record.

Review depth: full

| Task | Title | Deps | Files |
|------|-------|------|-------|
| T002 | Fix wave 1 cycle 1 review findings in T001 | T001 | docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md, prd/project-state/data/roadmap.json, prd/project-state/roadmap.md, tests/test_post_ship_pointers.py, tests/test_project_state_roadmap_freshness.py |

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

## Wave 3 — fix wave 1 cycle 2 review findings

Goal: Repair the blocking findings of the wave 1 cycle 2 review without changing source task contracts.
Review depth: full

| Task | Title | Deps | Files |
|------|-------|------|-------|
| T003 | Fix wave 1 cycle 2 review findings in T001 | T001, T002 | .project/WORKFLOW-NOTES.md, prd/project-state/data/roadmap.json, prd/project-state/roadmap.md, tests/test_post_ship_pointers.py, tests/test_project_state_roadmap_freshness.py |
