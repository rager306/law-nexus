---
id: T001
title: Add reference-package build/check to law-nexus-inspect, fixture-proven
wave: 1
deps: []
status: done
agent: build_t001
base: 6c905a4d94d8454408b13f94f71bb032c76d748b
worktree: null
task_branch: null
files:
  - crates/ln-product-cli/Cargo.toml
  - crates/ln-product-cli/src/main.rs
  - crates/ln-product-cli/tests/reference_package_cli.rs
---

# T001 — Add reference-package build/check to law-nexus-inspect, fixture-proven

## Context

`ln_consultant_parser::reference_layer` already proves the ADR-0031 reference
layer: `try_derive(DeriveOptions)` derives the artifact set, `references_document`
and `pageindex_document` render documents, `run_check` byte-checks artifacts
against the derivation, `measurement_applicable`/`MEASUREMENT_EDITION` scope the
ed-50 measurements, and `EXIT_OK/EXIT_ARGV/EXIT_INPUT` (+ drift exit 6) fix the
D6 exit contract (5 reserved, not emitted). The standalone binary
`crates/ln-consultant-parser/src/bin/reference_layer.rs` composes these today;
`law-nexus-inspect` (`crates/ln-product-cli/src/main.rs`, manual argv parsing,
health/inspect/replay/subordinates) does not expose them, and the package has
two binaries with no `default-run`, so the README quick-start command fails.
Fixture: the tracked measure-ed50 corpus and its two-row catalog (see
`scripts/test_m217_reference_parity.py`, `MEASURE_FIXTURE`/`MEASURE_CATALOG_ROWS`).

## Approach

- Mirror the standalone binary's flag handling (`--corpus-dir`, `--catalog`,
  `--out-dir`) in `main.rs`'s manual parser; unknown/missing flags exit 2
  (`EXIT_ARGV`), unreadable/missing inputs (including a corpus directory with
  zero XML documents) exit 3 (`EXIT_INPUT`), byte drift exits 6, success 0.
- Reuse the `reference_layer` module helpers; do not copy derivation logic and
  do not change any committed artifact byte-format.
- `check` must handle every drift row on its exit path — no warn-and-pass
  (INTENT N1/SC2); a zero-byte artifact is drift (INTENT E2).
- Re-running build into the same out-dir overwrites its artifacts cleanly and
  byte-identically; unrelated files in out-dir are left alone (INTENT E1).
- ATTEMPT-2 RECOVERY NOTE (owner ruling A, 2026-10-31): attempt 1's retained
  coder edits (the product source and the new test file in this crate, plus
  `default-run` in Cargo.toml) stay in this worktree. Their undeclared
  rusqlite dev-dependency and Cargo.lock change were ruled out of scope: the
  declared `files` list is binding. Build the measure-ed50 fixture catalog
  inside the test within the declared files only - e.g. shell out to the
  repository's Python recipe (`scripts/test_m217_reference_parity.py`,
  `build_catalog`) via `uv run --frozen python -c ...`, or use another
  std-only approach that writes the catalog into a temp dir. Do not add
  dependencies or touch undeclared files.
- Build writes only inside `--out-dir`; the corpus and catalog stay
  byte-unchanged (INTENT N2/SC1) — pin with a hash test.
- Corpora without edition 50: report measurements explicitly not applicable and
  exit 0 (`measurement_applicable` branch); corpora with edition 50 compare
  measurements normally.
- Add `default-run = "law-nexus-inspect"` to `crates/ln-product-cli/Cargo.toml`
  so the README quick-start command works as written.

## Interface contract

None

## Intent coverage

- SC1
- SC2
- SC3
- SC4
- SC5
- SC6
- SC7

## Acceptance criteria

1. (SC1, E1, N2) `reference-package build` on the measure-ed50 fixture exits 0 and writes the expected artifact set into `--out-dir`; a second build into the same dir succeeds byte-identically and touches nothing outside it; corpus and catalog hashes are unchanged.
2. (SC2) `reference-package check` on the unmodified package exits 0; after any artifact byte is modified it exits 6.
3. (SC3) Builds into two different temp dirs are byte-identical.
4. (SC4, E2) A missing catalog, an absent corpus dir, and an empty corpus directory each exit 3; a zero-byte artifact exits 6.
5. (SC5) An unknown flag and a missing required flag each exit 2.
6. (SC6) A corpus without edition 50 builds and checks with measurements explicitly marked not applicable, exit 0.
7. (SC7) `cargo run -q -p ln-product-cli -- health` exits 0 exactly as the README writes it.

## Verify

```bash
test -f crates/ln-product-cli/tests/reference_package_cli.rs && cargo fmt --all --check && cargo test -p ln-product-cli --offline --test reference_package_cli && cargo run -q -p ln-product-cli -- health
```

Heavy: no

## Log

- 2026-10-31 — created by planner (quick mode)
- 2026-10-31 — attempt 1 timed out at the configured 900s limit (owner raised it to 3600s and approved the retry); coder work retained in the primary worktree; task reset to pending for attempt 2
- 2026-10-31 — attempt 2 finished the retained work: replaced attempt 1's out-of-scope rusqlite catalog builder with the owner-approved std-only shell-out to the repo recipe (`scripts/test_m217_reference_parity.py` `build_catalog` + `MEASURE_CATALOG_ROWS` via `uv run --frozen python -c`), dropped its stray Cargo.toml blank line, rustfmt'd the two declared Rust files (attempt 1 never ran fmt); Verify passed exit 0: fmt --all --check clean, `cargo test -p ln-product-cli --offline --test reference_package_cli` 8/8 ok, `health` exit 0; changed paths: the three declared files only
- 2026-10-31 — authoritative Verify (orchestrator finish of attempt 2): exit 0 in sidecar gsd-path-verify/task-t001-verify — fmt clean, 8/8 acceptance tests (SC1-SC7 incl. E1 idempotency+input-safety, E2 zero-byte drift, byte-identical dirs, edition-50 applicability, argv 2/3/6 paths); evidence: .git/gsd-path/dispatch/gsd-path-M011/T001/attempt-2/verify.json
