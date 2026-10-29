# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_repository_quality_gate.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC2 |
| SC3 | T002 | AC1 |
| SC4 | T001 | AC3 |
| SC4 | T002 | AC2 |

## Config

- max_review_cycles: 3
- wave_budget: none
- review_panel: off
- finding_skeptics: off

## Wave 1 — align the tracked surfaces

Goal: make the CI inventory, the agent entry point, the roadmap history and the
current-state pointer describe the shipped world.

Review depth: full

| Task | Title | Deps | Files |
|------|-------|------|-------|
| T001 | Name the pointer suites in the CI inventory and the refresh rule in AGENTS.md | — | prd/migration/decommission/repository-quality-gate.json, tests/test_repository_quality_gate.py, AGENTS.md, tests/test_ci_runtime_restore.py |
| T002 | Complete the roadmap history and refresh the current-state pointer | T001 | prd/project-state/roadmap.md, docs/agent-stack/POST-SHIP-STATE-2026-10-28.md, tests/test_post_ship_pointers.py |

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E1 | T001 | tests/test_repository_quality_gate.py |

## Surface contract

### ci workflow (repository-quality.yml) — T001

Criteria: SC1, SC2
Entry: a terminal on the bound branch gsd-path/M010; `uv run --frozen pytest tests/test_repository_quality_gate.py -q`.
States: inventory names the CI suites → 0 failures; a dropped suite → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.

### roadmap projection (prd/project-state) — T002

Criteria: SC3, SC4
Entry: a terminal on the bound branch gsd-path/M010; `uv run --frozen pytest tests/test_post_ship_pointers.py -q`.
States: history and pointer complete → 0 failures; a missing bullet → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.
