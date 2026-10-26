---
id: T003
title: Land the CI policy and payload type-check package
wave: 1
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - .github/workflows/repository-quality.yml
  - src/law_nexus_harness/workflow_state.py
  - tests/test_harness_workflow_state.py
---

# T003 — Land the CI policy and payload type-check package

## Context

SC9's small package closes three named residuals. First, the m207 schema check runs in CI under an unconditional shell-truth fallback: the M207 S04 portable-parts step pipes `uv run python scripts/m207_s04_schemas.py check` through a silenced `|| true`, so a real schema failure can never fail the job. Second, the corpus-integration job's comment claims a self-hosted runner sets LAW_NEXUS_CORPUS_AVAILABLE=1 while the job runs on the GitHub-hosted label ubuntu-latest — research showed the job cannot route to a self-hosted runner at all, and the corpus exposure ruling (2026-10-26, runner-only) keeps the job skipped in this milestone with no routing change. Third, workflow_state.py silently reads a present optional identity field of the wrong type as absent, the exact gap E9 rules on. N3 forbids introducing any new blanket suppression while closing the first residual.

## Approach

- Make the schema check blocking: the portable-parts step runs `uv run python scripts/m207_s04_schemas.py check` with its exit code asserted and its output visible; remove the silenced fallback. Run the check locally first — if it surfaces an unknown failure (the unplanned-fix-work risk INTENT flags), block with NEEDS-ORCHESTRATOR instead of suppressing it. The known documented conflicts stay exactly as they are: the frozen-token D466/D487 report-only steps and the migration-record items keep their documented continue-on-error status (E9 draws the advisory line; N3 forbids new suppression).
- Keep the corpus-integration job's runs-on and if lines byte-identical. Rewrite only the comment to state the actual setup: a GitHub-hosted label where the gitignored corpus is absent, so the job stays skipped unless a repository variable is set — and setting it on a hosted runner would fail the strict environment hard; any future strict target is a restricted self-hosted label per the runner-only ruling. No LAW_NEXUS_CORPUS_AVAILABLE value is set anywhere.
- Tighten the adapter in src/law_nexus_harness/workflow_state.py: a native status payload whose optional identity field (milestone or phase, in state or route) is present with a non-string value is rejected with the adapter's typed, fail-closed error; missing or null still yields a verdict. Extend tests/test_harness_workflow_state.py with regressions covering all four field sites and both sides of the rule (E9).
- tests/test_repository_quality_gate.py pins required workflow commands and must keep passing unmodified.

## Interface contract

- None

## Intent coverage

- SC9

## Acceptance criteria

1. The m207 schema check no longer runs under an unconditional `|| true` in .github/workflows/repository-quality.yml; `uv run --frozen python scripts/m207_s04_schemas.py check` exits 0 as a blocking command; the diff introduces no new blanket suppression — no new unconditional truth fallback and no undocumented continue-on-error (N3).
2. The corpus-integration comment states the actual setup — hosted label, corpus absent, job stays skipped, no LAW_NEXUS_CORPUS_AVAILABLE value set — while runs-on and if are unchanged; no routing change (runner-only ruling).
3. E9: workflow_state rejects a present optional identity field of the wrong type with a typed, fail-closed error while accepting missing and null values; regression tests in tests/test_harness_workflow_state.py pin both sides for milestone and phase in state and route.
4. The known documented conflicts stay advisory and untouched: the frozen-token and migration-record report-only steps keep their documented continue-on-error status (E9 boundary).

## Verify

```bash
uv run --frozen python scripts/m207_s04_schemas.py check && uv run --frozen pytest tests/test_harness_workflow_state.py -q && ! grep -q "|| true" .github/workflows/repository-quality.yml
```

Heavy: no

## Log

- 2026-10-26 — created by planner
