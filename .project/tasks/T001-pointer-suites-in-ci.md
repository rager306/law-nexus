---
id: T001
title: Run the pointer suites in CI
wave: 1
deps: []
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - .github/workflows/repository-quality.yml
  - tests/test_ci_runtime_restore.py
---

# T001 — Run the pointer suites in CI

## Context

The roadmap projection has drifted after every ship since M003 and was found by
hand each time, most recently after the M007 integration on main 50386e26: two
tests fail there (`test_roadmap_json_current_milestone_tracks_the_latest_archive`
and `test_native_marker_names_the_operational_milestone`). Neither suite is in
the CI list, so the drift reaches main silently.

## Approach

- Add both pointer suites to the CI suite list.
- Pin their presence in `tests/test_ci_runtime_restore.py`.

## Interface contract

- None

## Intent coverage

- SC1
- SC3

## Acceptance criteria

1. Both pointer suites run in CI, so a stale projection fails a job (E1: a list that omits either fails the pin).
2. No suite is removed from the list to make it pass (N1).

## Verify

```bash
uv run --frozen pytest tests/test_ci_runtime_restore.py -q -k 'pointer'
```

## Log

- 2026-10-28 — created by plan (quick mode)
