---
id: T002
title: Make the governor honesty step name the missing proof input
wave: 2
deps: [T001]
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - .github/workflows/repository-quality.yml
  - tests/test_ci_runtime_restore.py
---

# T002 — Make the governor honesty step name the missing proof input

## Context

The migration job passes `fetch-depth: 0` and sets `origin/HEAD`, yet its
governor step still reports `kind=conflicting-ownership` with reason
`current branch main != STATE.branch gsd-path/M006`. The generic block does not
say which proof input is missing, so the defect is not diagnosable from the job
log. The step must print the observed surface and the resolved proof inputs
before it exits.

## Approach

- Print the observed surface and the proof-input state in the honesty step.
- Keep every existing failure condition fatal; only add diagnosis.
- Pin the diagnostic in `tests/test_ci_runtime_restore.py`.

## Interface contract

- None

## Intent coverage

- SC2
- SC3

## Acceptance criteria

1. A non-shipped surface exits non-zero and the log names the observed surface plus the proof-input state (E2).
2. No existing assertion is removed or weakened; the step still fails on a lying surface (N2).

## Verify

```bash
uv run --frozen pytest tests/test_ci_runtime_restore.py -q -k 'governor or honesty'
```

## Log

- 2026-10-28 — created by plan (quick mode)
