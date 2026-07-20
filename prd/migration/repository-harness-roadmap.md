# Python repository harness roadmap

**Status:** `[proposed]`.  
**Authority:** ADR-0007, R064.  
**Boundary:** process-level orchestration only; Rust owns all product behavior.

## Objective

Consolidate scattered repository verification scripts into one Python CLI that
controls architecture, ADRs, Cargo quality, parity artifacts, performance,
document freshness, CI/GSD integration and diagnostics without implementing or
importing product logic.

Provisional entrypoint:

```bash
python -m law_nexus_harness <group> <command>
```

## Architecture

```text
harness/law_nexus_harness/
├── __main__.py
├── cli.py                 # argparse dispatch only
├── model.py               # result/diagnostic records
├── process.py             # bounded subprocess execution
├── architecture.py        # Cargo metadata + declarative edge rules
├── adr.py                 # ADR metadata/index/supersession checks
├── cargo.py               # fmt/clippy/test/audit orchestration
├── parity.py              # frozen manifest comparison
├── performance.py         # benchmark report comparison
├── docs.py                # README/CHANGELOG/ADR/architecture freshness
├── ci.py                  # composed read-only profiles
└── status.py              # compact JSON/human summary
```

Stdlib-first. Rust binaries emit semantic counts/results; the harness only
validates process/report contracts and compares frozen values.

## Thin slices

### H01 — Process runner and stable diagnostics

**Depends:** ACP decommission D1 (git-lex hook disconnected).

Deliver:

- subprocess runner with timeout, cwd allowlist, bounded stdout/stderr;
- stable result fields: command ID, phase, status, exit code, duration,
  diagnostics, artifacts, fingerprints, non-claims;
- secret/path redaction;
- unit tests for success, non-zero, timeout, missing binary and truncation.

Demo: harness launches `cargo --version` and a harmless Rust stub binary, emits
one deterministic JSON result, and surfaces a forced failure.

### H02 — Architecture and ADR checks

**Depends:** H01, decommission D2.

Deliver:

- parse `cargo metadata` and enforce allowed crate edges from a declarative file;
- ensure core has no I/O/runtime dependencies;
- ADR metadata, status, supersession, index and source-anchor checks;
- migrate the reusable substance of `verify-adr-conformance.py` without ACP/D098
  vocabulary;
- archive or retire duplicate standalone verifiers only after parity tests.

Demo: valid workspace passes; forbidden `core -> parser` edge and malformed ADR
fail with stable reason codes.

### H03 — Cargo quality profile

**Depends:** H01 and initial Cargo workspace.

Commands:

```text
harness cargo fmt
harness cargo clippy
harness cargo test
harness cargo audit
harness cargo deny
harness cargo check
```

Each wraps a pinned documented command and aggregates results. Tool absence is
`blocked`, not a false pass.

### H04 — Documentation freshness

**Depends:** H02.

Deliver checks for:

- `README.md` current commands/crates;
- `CHANGELOG.md` entry for product/architecture changes;
- `doc/adr/README.md` includes every current ADR and no rejected ADR;
- `prd/ARCHITECTURE.md` matches current milestone and workspace;
- requirements/roadmap references resolve;
- generated document sections carry source fingerprints and `--check` support.

Demo: stale README and missing ADR index entries fail; current docs pass.

### H05 — Parity manifest and artifact checks

**Depends:** baseline reconciliation and Rust parser outputs.

- load frozen source/output manifest;
- launch Rust binaries with explicit args;
- compare hashes, semantic counts, reason-code sets and schemas;
- distinguish exact parity, intentionally stricter safety, expected format
  migration and regression;
- never rebuild Python product artifacts inside freshness checks.

Demo: canonical Rust artifact passes; one modified ID/count/reason fails with a
small diff.

### H06 — Performance, memory and concurrency

**Depends:** H01, Rust parser benchmark surface.

- run defined scenarios from `rust-performance-baseline.md`;
- collect wall/CPU/peak RSS/throughput/speedup/variance;
- enforce accepted budgets;
- persist last result and compact comparison against baseline;
- include host/toolchain/input manifest.

Demo: current corpus and 10× replay produce comparable machine-readable reports;
a deliberately low budget fails.

### H07 — CI and GSD integration

**Depends:** H02–H06.

- replace the old compliance workflow with harness/Cargo profiles;
- fast profile for commits/PRs, full corpus/benchmark profile separately;
- map failures to actionable reason codes;
- feed compact reports to GSD evidence without `.gsd/exec` as durable anchors;
- no outward mutation or remote publish.

### H08 — Harness boundary audit

**Depends:** H07.

Final checks:

- no PyO3, FFI/shared-library loader or Rust package import;
- no imports from Python product code;
- no legal/parser/graph/retrieval policy implementation;
- all product execution crosses subprocess boundary;
- harness can be deleted/replaced without changing Rust behavior.

## Command contract

```text
architecture check
adr check
cargo check [--fast|--full]
parity check [manifest]
performance check [scenario]
docs check
ci check [profile]
status [--json]
```

Exit codes:

- `0` pass;
- `1` contract/regression failure;
- `2` usage/config error;
- `3` blocked dependency/tool;
- `4` timeout/resource budget;
- `5` internal harness failure.

## Observability

Every command emits a bounded JSON record and optional human rendering. It
persists no credentials or raw legal text. Failure state names phase, reason,
command ID, duration, retryability and report path.

## Definition of done

The harness is complete when architecture, ADR, Cargo, parity, performance,
docs and CI profiles are usable; negative fixtures prove failures are visible;
no product/domain logic exists in Python; and Rust behavior is unchanged if the
harness is removed.
