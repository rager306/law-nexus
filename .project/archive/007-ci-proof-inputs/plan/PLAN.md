# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_ci_runtime_restore.py tests/test_harness_governor.py tests/test_harness_preflight.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T002 | AC1 |
| SC3 | T001 | AC2 |
| SC3 | T002 | AC2 |

## Wave 1 — supply the proof inputs

Goal: give the rust job the full history and tags the integration proof needs.

Review depth: full

## Wave 2 — name the missing proof input

Goal: make the migration job's governor step diagnose its own failure.

Review depth: full

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E2 | T002 | tests/test_ci_runtime_restore.py |

## Surface contract

### ci workflow (repository-quality.yml) — T001

Criteria: SC1, SC3
Entry: a terminal on the bound branch gsd-path/M007; `uv run --frozen pytest tests/test_ci_runtime_restore.py -q`.
States: both checkout inputs pinned → 0 failures; a dropped input → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.
