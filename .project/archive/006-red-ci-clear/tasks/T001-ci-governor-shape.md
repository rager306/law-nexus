---
id: T001
title: Pin the shipped-surface shape in the governor honesty step
wave: 1
deps: []
status: done
agent: build_T001
base: df8193125af126d9cb7d1b1b7102ad1b897f508e
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
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  ...............                                                          [100%]
  15 passed in 2.74s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 1.45s
  ```
