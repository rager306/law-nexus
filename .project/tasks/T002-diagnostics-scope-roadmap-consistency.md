---
id: T002
title: Publish governor diagnostics on any migration-job failure and verify roadmap consistency
wave: 1
deps: []
status: pending     # orchestrator-owned
agent: null
base: null
worktree: null
task_branch: null
files:
  - .github/workflows/repository-quality.yml
  - tests/test_project_state_roadmap_freshness.py
---

# T002 — Publish governor diagnostics on any migration-job failure and verify roadmap consistency

## Context

The governor-diagnostics artifact step runs only after the governor step (`if: failure()` on that step); the pytest step precedes it, so a pytest failure publishes nothing (observed in CI run 40533158703). Move the artifact publication to job-failure scope (`if: failure()` at job level), preserving the non-zero exit (N3). Then confirm the roadmap consistency (SC4): the three-way identity test passes with the marker naming the M002 continuation.

## Approach

- Move/adjust the `governor-diagnostics` artifact step to `if: failure()` at job level (publishes on any failing step).
- Run the roadmap consistency test to confirm SC4.

## Interface contract

- None

## Intent coverage

- SC3
- SC4

## Acceptance criteria

1. The diagnostics artifact step carries `if: failure()` at job level (publishes on any failed step).
2. The roadmap consistency test passes with the marker naming the M002 continuation (SC4).
3. The job exit stays non-zero when any step fails (no suppression, N3).

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
```

## Log

- 2026-10-27 — created by plan (quick mode)
