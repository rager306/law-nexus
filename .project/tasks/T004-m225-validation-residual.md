---
id: T004
title: Close the M225 validation residual with an honest re-run
wave: 2
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
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
