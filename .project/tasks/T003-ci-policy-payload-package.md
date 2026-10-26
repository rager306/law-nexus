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

1. The m207 schema check becomes a loud blocking CI step: `.github/workflows/repository-quality.yml` runs `uv run --frozen python scripts/m207_s04_schemas.py check` with its exit code asserted and its output visible; the ONLY tolerated failures are the two known documented signatures — `CORPUS_COUNT_DRIFT` (gitignored-corpus absence) and `S03_RATE_IMPORTED` (frozen-token D466/D487) — which the step reports as advisory; any other finding, or a failure whose output is not fully accounted for by those two signatures, fails the job. The diff introduces no new blanket suppression — no unconditional truth fallback and no undocumented continue-on-error (N3). The bare command itself is NOT required to exit 0: E9 keeps the two known conflicts advisory (orchestrator answer 2026-10-26).
2. The corpus-integration comment states the actual setup — hosted label, corpus absent, job stays skipped, no LAW_NEXUS_CORPUS_AVAILABLE value set — while runs-on and if are unchanged; no routing change (runner-only ruling).
3. E9: workflow_state rejects a present optional identity field of the wrong type with a typed, fail-closed error while accepting missing and null values; regression tests in tests/test_harness_workflow_state.py pin both sides for milestone and phase in state and route.
4. The known documented conflicts stay advisory and untouched: the frozen-token and migration-record report-only steps keep their documented continue-on-error status (E9 boundary).

## Verify

```bash
uv run --frozen pytest tests/test_harness_workflow_state.py -q && uv run --frozen python -c "import yaml,sys; w=yaml.safe_load(open('.github/workflows/repository-quality.yml')); steps=[s for j in w['jobs'].values() for s in (j.get('steps') or []) if 'm207_s04_schemas' in str(s.get('run',''))]; assert steps, 'schema step missing'; runs=' '.join(str(s.get('run','')) for s in steps); assert '|| true' not in runs, 'schema step still silenced'; assert 'CORPUS_COUNT_DRIFT' in runs and 'S03_RATE_IMPORTED' in runs, 'known-conflict advisory line missing'; print('workflow schema-gate ok')"
```

Heavy: no

## Log

- 2026-10-26 — created by planner
- 2026-10-26 — Orchestrator answer: reading (a) is pinned by the approved artifacts — E9 keeps exactly CORPUS_COUNT_DRIFT and S03_RATE_IMPORTED advisory while unknown failures block, SC9 requires the de-silenced blocking step, N3 forbids new suppression — cited: `.project/intent/INTENT.md` Edge coverage E9, Prohibitions N3, SC9; `.project/research/SYNTHESIS.md` decision “Strict corpus job in M001 — SC9 fix shape”. Readings (b) and (c) rejected — (b) masks findings beyond the ruling, (c) contradicts SC9.
- 2026-10-26 — plan-defect repair (orchestrator, per build-native step 2): AC1 and Verify reworded to the E9-pinned advisory-allowlist semantics (the bare schema command exits 1 on the two known documented conflicts in every environment; scripts/m207_s04_schemas.py is outside this task's files). Task returned to pending for redispatch at a fresh base.

- 2026-10-26 — NEEDS-ORCHESTRATOR: AC1 and the Verify chain require `uv run --frozen python scripts/m207_s04_schemas.py check` to exit 0 as a blocking command, but measured reality is exit 1 in every environment that exists — corpus-absent clone/CI runner: 2 findings (CORPUS_COUNT_DRIFT: declared consultant root consru_export/consru_export/exports absent; S03_RATE_IMPORTED), primary /root/law-nexus with the corpus present: 1 finding (S03_RATE_IMPORTED: tracked frozen witness crates/ln-consultant-parser/src/amendment_provenance.rs:2789 carries 'm207-s04' while the frozen schema pin $.s03_isolation.crates_reference_patterns=['m207-s03','m207_s03','m207-s04','m207_s04'] bans it) — and scripts/m207_s04_schemas.py (no advisory-filter mode, argparse offers only check/selftest/--root/--protocol/--schemas) is not in T003's files, so no edit inside `files` can make the command exit 0; unblocking the bare command as written turns both documented conflicts (E9: frozen-token D466/D487 and gitignored-corpus drift stay advisory; supplied spec §3 lists S03_RATE_IMPORTED among results that «остаются в логе, но не блокируют») into blocking failures and leaves CI and the task Verify permanently red — readings: (a) CI step asserts the check loudly with a narrow, documented advisory line for exactly these two known signatures and any other finding fails the job, which needs AC1/Verify reworded (planner-owned) to "unknown findings fail"; (b) plan change adding scripts/m207_s04_schemas.py to files and a documented portable/known-findings mode so the command exits 0 with both conflicts staying advisory; (c) scope the blocking-schema residual out of T003 (contradicts the supplied-spec divergence the task exists to close).

- 2026-10-26 — implemented (r1, base 0c502255a94c188f29ef48019403ab7cd6308192), all four ACs: (1) `.github/workflows/repository-quality.yml` — the M207 S04 portable-parts step now runs `uv run --frozen python scripts/m207_s04_schemas.py check` with its exit code asserted (PIPESTATUS) and its output visible (tee); an inline advisory allowlist keeps exactly the two documented signatures CORPUS_COUNT_DRIFT and S03_RATE_IMPORTED (every output line must be a known finding or the FAIL M207_S04_SCHEMAS_GATE summary, and at least one known finding is required) and fails the job on any other finding, an empty failure output, or any unaccounted line — the silenced shell-truth fallback is removed, no `continue-on-error` added (N3); battery preamble comment amended to name the two advisory signatures; corpus-integration comment rewritten to the actual setup (GitHub-hosted ubuntu-latest label, gitignored corpus absent, job stays skipped unless the repository variable is set, setting it on a hosted runner would fail the strict environment hard, no LAW_NEXUS_CORPUS_AVAILABLE value set anywhere, future strict target = restricted self-hosted label per the runner-only ruling) with `runs-on` and `if` byte-identical. Local pre-check at this base: the check emits exactly the two known signatures (CORPUS_COUNT_DRIFT corpus-absent; S03_RATE_IMPORTED amendment_provenance.rs 'm207-s04') — no unknown failure, so no block. Gate logic exercised against 7 synthetic outputs (known-two → advisory pass; ok → pass; unknown / mixed / empty-failure / summary-only / plain-text → fail) plus one real run → all classified correctly. (2) `src/law_nexus_harness/workflow_state.py` — E9: `_identity_field` now takes `where` and raises the adapter's typed `_NativeStatusError` ("native status payload <where>.<field> must be a string when present, got <type>") for a present non-string value; missing, null and empty-string still read as absent; all four sites (state.milestone, state.phase, route.milestone, route.phase) are validated before the state→route fallback so a wrong-typed route value cannot hide behind a valid state twin; surfaces as INVALID_SCHEMA with readiness blocked. (3) `tests/test_harness_workflow_state.py` — added `test_wrong_typed_identity_field_fails_closed` (8 rejection cases across all four field sites) and `test_identity_fields_accept_null_and_missing_across_all_four_sites` (3 acceptance payloads); ruff check/format and basedpyright/ty/pyrefly pass on the edited file; `tests/test_repository_quality_gate.py` passes unmodified. Verify: `uv run --frozen pytest tests/test_harness_workflow_state.py -q && uv run --frozen python -c "import yaml,sys; ... assert '|| true' not in runs ...; print('workflow schema-gate ok')"` → `40 passed in 0.54s` + `workflow schema-gate ok`, exit 0. Changed paths: .github/workflows/repository-quality.yml, src/law_nexus_harness/workflow_state.py, tests/test_harness_workflow_state.py.
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T003): pass, exit 0; output tail:
  ```
  ........................................                                 [100%]
  40 passed in 0.50s
  workflow schema-gate ok
  ```
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T003): pass, exit 0; output tail:
  ```
  ........................................                                 [100%]
  40 passed in 0.55s
  workflow schema-gate ok
  ```
- 2026-10-26 — orchestrator: first finish attempt blocked — the verify sidecar was prepared at base 0c502255 whose .gitignore predates the /build/, /archive/ anchoring that T002 landed (99abed61); the preflight reads the sidecar's ignore rules. Contract unchanged and valid; clean retry at the current head per the recovery rule; the r1 work diff is preserved verbatim at /root/law-nexus-pre-milestone-fix/t003-r1-work.patch.
