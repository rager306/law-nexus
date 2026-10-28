---
id: T001
title: Give the rust job the full history and tags the integration proof needs
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

# T001 — Give the rust job the full history and tags the integration proof needs

## Context

CI run 40697747035 fails "Product and architecture harness tests" in the rust
job. Its checkout runs with `--depth=1` and no tags, so the pinned native status
helper cannot see the milestone tag and reports the integration unverified; the
governor then reports conflicting-ownership and the live surface test fails
(`assert 'fail' == 'pass'`). Reproduced locally: a depth-1 clone without tags
yields `completion unverified | missing milestone tag`; the same tree with the
full history and tags yields `verified` and a shipped-integrated governor.

## Approach

- Give the rust job the same checkout inputs the migration job already has:
  full history and tags.
- Pin both inputs in `tests/test_ci_runtime_restore.py`.

## Interface contract

- None

## Intent coverage

- SC1
- SC3

## Acceptance criteria

1. The rust job checks out the full history and tags, so the integration proof resolves and the governor reports shipped-integrated (E1).
2. The suite pins both checkout inputs and fails if either is dropped (N3).

## Verify

```bash
uv run --frozen pytest tests/test_ci_runtime_restore.py -q -k 'checkout or rust'
```

## Log

- 2026-10-28 — created by plan (quick mode)
