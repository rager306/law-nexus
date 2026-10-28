---
id: T002
title: Make the governor honesty step name the missing proof input
wave: 2
deps: [T001]
status: done
agent: build_T002
base: 3b2e1e4c49a7e08ab24c82f41adebdd2bbd8efac
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
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  ...                                                                      [100%]
  3 passed, 13 deselected in 1.54s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
  Installed 32 packages in 283ms
  ```
- 2026-10-28 — orchestrator regression Verify of T001 (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  ..                                                                       [100%]
  2 passed, 14 deselected in 0.37s
  ```
