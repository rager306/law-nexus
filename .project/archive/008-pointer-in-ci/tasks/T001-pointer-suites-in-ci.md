---
id: T001
title: Run the pointer suites in CI
wave: 1
deps: []
status: done
agent: build_T001
base: eac6fd994565c0a39717a6bed2bfa2bd2dfb122f
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
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  .                                                                        [100%]
  1 passed, 16 deselected in 1.33s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 311ms
  ```
