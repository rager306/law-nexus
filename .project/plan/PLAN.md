# Plan — law-nexus

<!-- Written by $gsd-path-plan (quick mode) for milestone post-ship-hardening-2 (M003). -->

Project verify: `uv run --frozen pytest tests/test_branch_context.py tests/test_harness_governor.py tests/test_harness_preflight.py tests/test_project_state_roadmap_freshness.py -q`

## Wave 1 — honest CI expectations and diagnostics coverage

Goal: honest CI expectations and diagnostics coverage

Review depth: full

Review depth: full

Tasks: T001 (scenario-expectation fix, STATE-phase-keyed), T002 (diagnostics artifact scope + roadmap consistency).

## Intent coverage

| Criterion | Task | Notes |
|-----------|------|-------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC4 |
| SC3 | T002 | AC1 |
| SC4 | T002 | AC2 |

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E2 | T001 | tests/test_branch_context.py |

## Surface contract

### terminal (native Path CLI: governor, pytest, git) — T001

Criteria: SC1, SC2
Entry: a terminal on the bound branch gsd-path/M003; `uv run --frozen pytest tests/branch_context.py tests/test_branch_context.py tests/test_harness_governor.py tests/test_harness_preflight.py -q`.
States: bound branch → full assertions pass; non-operational branch → fail-closed pins pass; milestone literals absent (grep pin green).
Walkthrough:
1. Run uv run --frozen pytest tests/branch_context.py tests/test_branch_context.py and confirm the classification matrix pins all five contexts × both STATE phases.
2. Run uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py -q and confirm 0 failures on the bound branch.
3. Run grep -n 'gsd-path/M0' tests/test_harness_governor.py tests/test_harness_preflight.py and confirm only fixture-payload whitelisted hits.

### GitHub Actions (repository-quality migration job on main: pytest result, diagnostics artifact) — T002

Criteria: SC3, SC4
Entry: the repository-quality workflow run on the integrated main head.
States: failure → the governor-diagnostics artifact publishes and the job exit stays non-zero; success → no artifact, job green.
Walkthrough:
1. Inspect the workflow YAML for `if: failure()` at the artifact step and the absence of suppression.
2. Verify the roadmap consistency test passes.
