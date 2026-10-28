---
id: T002
title: Publish governor diagnostics on any migration-job failure and verify roadmap consistency
wave: 1
deps: []
status: done
agent: build_T002
base: 5122b3138d87eec7affac0bd5ca23b94bdd7be7a
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
- 2026-10-28 — r2 (fresh base 5122b313; re-applies the verified r1
  implementation after the r1 dispatch record went stale).
  repository-quality.yml: governor report step now `if: always()` so
  governor.json exists whenever an earlier step (pytest, restore) failed; the
  governor-diagnostics upload keeps `if: failure()` at job-failure scope as
  the job's last step, so the artifact publishes on any migration-job failure
  while the exit stays non-zero (SC3, E4, N3).
  tests/test_project_state_roadmap_freshness.py: three-way marker test
  re-keyed on STATE phase semantics (SC4/E5) — shipped/done requires exact
  STATE = roadmap.json = live-marker identity; in-flight requires
  latest-archived = roadmap.json = live-marker, keeping STATE honestly ahead
  (the documented roadmap-current-tracks-path mismatch on integrated main);
  adds pins for the job-failure-scoped artifact, the always() payload, and
  no-exit-masking (no milestone-branch literals introduced).
  Verify: `uv run --frozen pytest
  tests/test_project_state_roadmap_freshness.py -q` → 5 passed, 5 skipped,
  exit 0. Regression: tests/test_ci_runtime_restore.py (15) +
  tests/test_repository_quality_gate.py (5) → 20 passed; ruff check + format
  clean on the touched test file.
- 2026-10-28 — orchestrator Verify (isolate gsd-path-task/T002): pass, exit 0; output tail:
  ```
  sssss.....                                                               [100%]
  5 passed, 5 skipped in 4.88s
  ```
