# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q -k 'not test_native_marker_names_the_operational_milestone' && uv run --frozen pytest tests/test_post_ship_pointers.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC1 |
| SC3 | T002 | AC1 |

## Wave 1 — pointer refresh

Goal: refresh all live pointers to M003 shipped state.

Review depth: full

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E2 | T001 | tests/test_project_state_roadmap_freshness.py |

## Surface contract

### terminal (native Path CLI: path-run.py status, governor, pytest, git) — T001

Criteria: SC1, SC2
Entry: a terminal on the bound branch gsd-path/M004; the commands python3 scripts/ai/path-run.py status, uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q.
States: bound branch → full assertions pass; stale pointers → test fails with named mismatch.
Walkthrough:
1. Run uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q and confirm the three-way identity test passes.

### GitHub Actions (repository-quality migration job on main) — T002

Criteria: SC3
Entry: the integrated main head's docs/agent-stack/ directory.
States: pre-ship → old dated report exists; post-ship → new dated report exists with AGENTS.md/AGENT_HANDOFF.md pointing at it.
Walkthrough:
1. Confirm docs/agent-stack/POST-SHIP-STATE-2026-10-28.md exists and AGENTS.md references it.
