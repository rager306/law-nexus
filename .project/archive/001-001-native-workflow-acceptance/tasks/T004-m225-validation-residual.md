---
id: T004
title: Close the M225 validation residual with an honest re-run
wave: 2
deps: []
status: done
agent: build_T004
base: 61effa6efe68df1efff2c71f4bd39c4b701e434c
worktree: null
task_branch: null
files:
  - prd/migration/rust-evidence/m225-validation-battery-2026-10-18.json
  - prd/migration/rust-evidence/m225-validation-rerun-m001.json
  - tests/test_m225_validation_residual.py
---

# T004 — Close the M225 validation residual with an honest re-run

## Context

M225 milestone validation returned needs-attention for exactly one residual: the battery at prd/migration/rust-evidence/m225-validation-battery-2026-10-18.json still carries tested_source_revision as the placeholder pending-fill-by-validate-unit, so the source pin never bound to a real revision. LEGACY_CROSSWALK is explicit: the S02 code is NOT missing — the reference-layer port is done, parity-tested, and frozen; this task must not re-implement any of it (INTENT scope-out). SC3 closes the residual natively: fill the pin, re-run native validation, record the honest verdict with its measurement class. The corpus is absent from every isolated task environment by design, so the re-run is hermetic; INTENT accepts an honestly inconclusive parity verdict and forbids (N1) recording a corpus-absent hermetic green run as a byte-parity PASS.

## Approach

- In the isolated task tree at the recorded base, capture `git rev-parse HEAD` before validating — that full 40-hex SHA is the exact tree state the re-validation runs at (E3: any mismatch invalidates the battery; the task's own record edits do not affect the validated product surface).
- Re-run the hermetic validation surface natively and capture real outputs: `cargo test -p ln-consultant-parser --offline --no-fail-fast` (corpus-dependent tests skip visibly), `cargo fmt --all -- --check`, `cargo check -p ln-consultant-parser --offline`, and `uv run --frozen python scripts/verify-adr-conformance.py`. The battery's governor and preflight checks are environment-gated (branch-locked, fail-closed): record them as not re-run in isolation; the orchestrator's bound-branch governor run at the wave gate is the supporting evidence.
- Edit the battery JSON minimally: set tested_source_revision to the captured 40-hex SHA; rewrite tested_source_revision_role to state the E3 semantics — the full 40-hex SHA of the exact HEAD the re-validation ran at — replacing the stale Pi-aggregate placeholder wording; annotate the environment block with the native re-run context (runner and git_state). The 15 historical check entries, their outputs, and the timestamps stay byte-identical: this is the sanctioned residual close-out, not a rewrite of historical evidence (standing ruling).
- Create the new rerun record as the sibling file prd/migration/rust-evidence/m225-validation-rerun-m001.json (schema law-nexus/milestone-validation-rerun/v1): it names the battery file, repeats the same tested_source_revision, accounts for every battery check id with an explicit disposition — re-run-passed-hermetic, skipped-corpus-absent, or not-rerun-environment-gated — and records a verdict whose measurement class states plainly that the re-run is hermetic observability, that corpus-bound parity evidence remains the 2026-10-18 corpus-present run pinned at its own revision, and that green here does not prove corpus scenarios ran (N1).
- Touch nothing under crates/: the landing diff covers exactly the three declared paths.
- Write tests/test_m225_validation_residual.py pinning the mechanical core: the battery pin matches a full 40-hex SHA and no longer holds the placeholder; the rerun record covers every battery check id with a disposition from the fixed set; battery and record carry the same revision; the verdict states its measurement class (E3 and N1).

## Interface contract

- None

## Intent coverage

- SC3

## Acceptance criteria

1. tested_source_revision in the battery is a full 40-hex SHA — the exact HEAD the re-validation ran at — and the placeholder string is gone; the role text states the 40-hex-HEAD semantics (E3).
2. The 15 historical check entries of the battery are byte-identical to their recorded state; only the pin, its role text, and the environment annotation changed.
3. The rerun record exists at prd/migration/rust-evidence/m225-validation-rerun-m001.json, covers every battery check id with an explicit disposition from the fixed set, and its verdict states the measurement class — a hermetic run is not a byte-parity PASS (N1), and corpus parity evidence remains the pinned 2026-10-18 corpus-present run.
4. No file under crates/ changes (S02 untouched); the landing diff touches exactly the three declared paths.
5. tests/test_m225_validation_residual.py pins criteria 1 and 3 mechanically and fails if the residual were reverted to the placeholder.

## Verify

```bash
uv run --frozen pytest tests/test_m225_validation_residual.py -q
```

Heavy: no

## Log

- 2026-10-26 — created by planner
- 2026-10-26 — build_T004: closed the SC3 residual natively at base HEAD 61effa6efe68df1efff2c71f4bd39c4b701e434c (branch gsd-path-task/T004). Captured `git rev-parse HEAD` before validating; re-ran the hermetic validation surface natively at that exact HEAD: `cargo test -p ln-consultant-parser --offline --no-fail-fast` (exit 0; 66 blocks / 412 passed / 0 failed / 2 corpus-absent SKIP lines; reference-layer surface 8 blocks / 30 passed, same partition as the 2026-10-18 run), `cargo fmt --all -- --check` (0), `cargo check -p ln-consultant-parser --offline` (0), `cargo check --workspace --offline` (0), `cargo clippy --workspace --all-targets --offline -- -D warnings` (0, zero warnings), `cargo metadata --no-deps --format-version 1 --offline` (0, 47 packages), `uv run --frozen python scripts/verify-adr-conformance.py` (0, ok / 0 findings), the 7 reference-layer suites under `M225_S01_REPO_ROOT=/nonexistent-lns03` (exit 0; exactly 13 SKIP lines = the battery's hermetic baseline; all green), `cargo test ... --test reference_layer_fail_closed` (7/0), bin build + `--test reference_layer_s02_pageindex_cli` (3/0), and the m217 pytest battery `uv run --frozen pytest -q scripts/test_m217_*.py` (exit 1: 37 passed / 1 corpus-gate skip / 1 documented corpus-bound test `test_check_mode_rederivation_is_byte_identical` fail-closed at exit 3 without the corpus — the reference script's contract-correct behavior; recorded under skipped-corpus-absent, not as a pass). Battery edited at text level in exactly three regions (git diff verified): tested_source_revision → the 40-hex HEAD; tested_source_revision_role → E3 40-hex-HEAD semantics; environment gains `native_rerun_m001` {runner, git_state}. The 15 historical check entries, their outputs, and the timestamps are byte-identical. New m225-validation-rerun-m001.json (schema law-nexus/milestone-validation-rerun/v1): 15/15 battery check ids dispositioned — 9 re-run-passed-hermetic / 4 skipped-corpus-absent / 2 not-rerun-environment-gated (governor, preflight: branch-locked fail-closed; the orchestrator's bound-branch wave-gate run is the supporting evidence) — verdict `measurement_class: hermetic-observability-corpus-absent` with the N1 disclaimers in the statement. New tests/test_m225_validation_residual.py pins the 40-hex pin + placeholder absence, role semantics, same-revision across battery/record, full check-id coverage with fixed-set dispositions, and the measurement class. No file under crates/ changed (git status: zero crates/ entries); landing diff = the three declared paths.
- 2026-10-26 — Verify: `uv run --frozen pytest tests/test_m225_validation_residual.py -q` → `5 passed in 0.59s`, exit 0, run at HEAD 61effa6efe68df1efff2c71f4bd39c4b701e434c on gsd-path-task/T004.
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T004): pass, exit 0; output tail:
  ```
  .....                                                                    [100%]
  5 passed in 0.23s
  ```
- 2026-10-26 — build_T004 r2: `uv run --frozen ruff format tests/test_m225_validation_residual.py` normalized the new test file (1 file reformatted, formatting only, no semantic change); `ruff format --check` now clean (pre-commit hook blocker resolved); no other file touched.
- 2026-10-26 — Verify (r2): `uv run --frozen pytest tests/test_m225_validation_residual.py -q` → `5 passed in 0.29s`, exit 0, run at HEAD 61effa6efe68df1efff2c71f4bd39c4b701e434c on gsd-path-task/T004.
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T004): pass, exit 0; output tail:
  ```
  .....                                                                    [100%]
  5 passed in 0.24s
  ```
