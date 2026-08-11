---
id: ADR-0007
title: Python repository control-plane harness for the Rust product
status: Accepted
lifecycle: "[validated]"
date: 2026-07-20
superseds: none
related: [ADR-0004, ADR-0005, D105, D106, M107-7xtx1c]
---

# ADR-0007: Python repository control-plane harness for the Rust product

## Status

**Accepted [validated].** The boundary is decided and realized: the consolidated
harness CLI lives at `src/law_nexus_harness/` (governor, preflight, parity
orchestration, ADR/Cargo/GSD/CI process orchestration) and contains no product/
domain logic, no PyO3/FFI. The product runtime is Rust-only (ADR-0004/0005).

## Context

The law-nexus product transitions completely to Rust (ADR-0004). The repository
still needs a low-friction control plane for architecture and ADR conformance,
Cargo quality gates, parity artifacts, documentation freshness, CI/GSD
integration, and compact diagnostics. Python is suitable for this repository
automation, but it must not become a hidden second implementation of product
behavior.

## Decision

**Keep one thin Python repository-control CLI [validated]** that invokes Rust
binaries and standard tools across process boundaries. It may read repository
metadata and generated reports. It must not import Rust in-process, expose PyO3
bindings, or implement product/domain behavior. The harness at
`src/law_nexus_harness/` realizes this boundary.

### Allowed responsibilities

- enforce workspace/crate dependency direction and the hexagonal/onion contract;
- validate ADR metadata, status, supersession, indexes, and source anchors;
- run and summarize `cargo fmt`, `cargo clippy`, `cargo test`, benchmarks,
  security/audit tools, and selected Rust binaries;
- compare Rust outputs with frozen parity/golden artifacts;
- verify `README.md`, `CHANGELOG.md`, ADR index, architecture documents,
  requirement coverage, and roadmap freshness;
- orchestrate CI and GSD checks and emit compact machine-readable diagnostics;
- launch Rust CLIs as subprocesses with explicit arguments, timeouts, exit-code
  handling, bounded output, and secret-safe logging.

### Forbidden responsibilities

- legal-domain models, validation rules, hierarchy semantics, temporal policy,
  deontic classification, citation policy, or legal authority decisions;
- XML/ODT parsing, relation extraction, NormStatement emission, graph
  materialization, retrieval, evidence assembly, or FalkorDB product adapters;
- product API or daemon runtime;
- PyO3, FFI, shared-library loading, or any in-process Rust bridge;
- duplicating Rust business rules to make a check pass;
- interpreting LLM output as product truth or legal authority.

### Harness shape

The target surface is one discoverable command, provisionally:

```text
python -m law_nexus_harness <command>
```

Initial command groups:

```text
architecture check     # crate graph + onion/hexagonal boundaries
adr check              # metadata, indexes, supersession, anchors
cargo check             # fmt + clippy + tests + audits
parity check            # Rust binaries vs frozen artifacts
performance check       # benchmark and memory/concurrency budgets
docs check              # README/CHANGELOG/ADR/architecture freshness
ci check                # composed non-mutating verification profile
status                  # compact JSON + human summary
```

The implementation should be stdlib-first. Third-party dependencies require a
measured maintenance benefit. Every command returns a stable non-zero exit code
on failure and emits a bounded JSON record suitable for CI/GSD ingestion.

### Architectural enforcement

The harness checks contracts; Rust owns behavior. Architecture rules are
represented declaratively where practical (for example allowed crate edges,
required ADR fields, and document freshness inputs) and checked without
importing application code. Rust compile-time/module visibility and Cargo
workspace structure remain the primary product architecture enforcement;
Python checks repository-wide policies that Cargo does not encode directly.

## Consequences

- **Easier — pragmatic repository maintenance.** Documentation and orchestration
  remain cheap to evolve without contaminating the Rust product core.
- **Easier — one control surface.** Existing scattered `verify-*.py` scripts can
  be consolidated behind stable commands and structured diagnostics.
- **Harder — boundary discipline.** Python can silently grow into product logic.
  The forbidden-responsibility list and review tests must fail closed when that
  happens.
- **Harder — two toolchains remain.** Rust is the product toolchain; Python is a
  repository-automation toolchain. This is accepted because there is no
  in-process bridge and no duplicated product implementation.
- **Revisit condition.** Move the harness to Rust if Python setup becomes a
  deployment/CI burden or if process startup dominates repository checks.

## Alternatives Considered

### Option A: Rust-only repository tooling

**Pros:** one language and one toolchain.
**Cons:** higher friction for document/YAML/JSON orchestration during migration;
slower iteration on non-product checks. May become attractive after cutover.

### Option B: Preserve many independent Python verifier scripts

**Pros:** minimal immediate work.
**Cons:** poor discoverability, duplicated command parsing/reporting, inconsistent
exit semantics, and stale-doc drift. Rejected in favor of one harness CLI.

### Option C: PyO3 bridge

**Pros:** direct calls and rich type exchange.
**Cons:** creates an in-process coexistence layer and blurs product ownership.
Rejected by explicit human decision. ADR-0006 is preserved only in
`python_archive/adr/rejected/`.

## Verification contract

ADR-0007 advances from `[proposed]` to `[bounded]` only when:

1. one harness CLI exists with architecture, ADR, Cargo, and docs commands;
2. commands emit stable JSON and meaningful exit codes;
3. tests prove forbidden product imports/logic are absent;
4. at least one Rust binary is orchestrated through a subprocess boundary;
5. failure diagnostics include command, phase, duration, exit code, and bounded
   stderr without secrets;
6. the harness has no PyO3/FFI/shared-library dependency.

## Non-claims

- The harness is not a product runtime and does not validate legal correctness.
- Subprocess orchestration success is not product readiness or live TEI/RuVector validation.
- Historical options discussing PyO3 are rejected alternatives, not active design.

## References

- ADR-0004, ADR-0005, D105, D106, M107-7xtx1c
- `src/law_nexus_harness/`
