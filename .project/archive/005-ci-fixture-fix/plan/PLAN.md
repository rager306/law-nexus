# Plan — law-nexus

Project verify: `uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py -q`

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC2 |

## Wave 1 — CI fixture co-update

Goal: make the live suites pass on integrated main.

Review depth: full

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E1 | T001 | tests/test_harness_governor.py |

## Surface contract

### terminal (native Path CLI: pytest, governor) — T001

Criteria: SC1, SC2
Entry: a terminal on the bound branch gsd-path/M005; `uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py -q`.
States: bound branch → 0 failures; stale fixture → named failure.
Walkthrough:
1. Run the command and confirm 0 failures.
