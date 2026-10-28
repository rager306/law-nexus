---
id: T001
title: Pin the shipped-surface shape in the governor honesty step
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

# T001 — Pin the shipped-surface shape in the governor honesty step

## Context

The main-branch governor step requires the literal archive path
`.project/archive/001-001-native-workflow-acceptance`, so it fails for every
later milestone; the pin test copies the same literal.

## Approach

- Assert the `kind=shipped-integrated;` shape and a `.project/archive/` path.
- Pin the shape in the test, and pin that no milestone literal returns.

## Interface contract

- None

## Intent coverage

- SC1
- SC3

## Acceptance criteria

1. The step fails when the surface reports shipped-integrated without any archive path, and passes for a later milestone's archive (E1).
2. The step still fails when the shipped-integrated shape is missing (N2).
3. No milestone literal remains in the step or its pin test (N1).

## Verify

```bash
uv run --frozen pytest tests/test_ci_runtime_restore.py -q
```

## Log

- 2026-10-28 — created by plan (quick mode)
