---
id: ADR-0004
title: Rust migration decision for law-nexus
status: Accepted
lifecycle: "[validated]"
date: 2026-07-18
superseds: none
related: [M107-7xtx1c, D098]
---

# ADR-0004: Rust migration decision for law-nexus

## Status

**Accepted [proposed]** — the decision is recorded, the migration plan is written
(`prd/migration/`), but no Rust code exists yet. This ADR moves to `[bounded]`
when the first Rust component (domain types) ships with parity tests, and to
`[validated]` when the full parser pipeline runs end-to-end in Rust with Python
removed from the hot path.

## Context

law-nexus currently runs on Python 3.13 with the following measured performance
baseline (M107 measurement, 2026-07-18):

| Workload | Wall time | Notes |
|---|---|---|
| Full corpus parse (284 MB, 81 files, 10 in-scope) | 7.5 s | `build-consultant-hierarchy-records.py --corpus` |
| Single-file parse (5 MB, 44-FZ) | 2.2 s | `build-consultant-hierarchy-records.py` |
| Test suite fast path (`pytest -m "not slow"`) | 32 s | 68 tests after M106 session-scoped fixtures |
| Test suite full path | ~10 min | 13 corpus-rebuilding tests, session-scoped fixtures |
| Test suite before M106 | 65+ min | 7× redundant corpus rebuilds (architecture, not language) |

The user hypothesized that "we will face performance questions as document count
grows." The M107 measurement shows the perceived slowness was a **test
architecture problem (7× redundant rebuilds), not a language problem** — full
corpus parse is already 7.5 s on Python. This ADR records the migration decision
in that light: Rust migration is a **scaling hedge and a concurrency story**, not
an emergency fix.

## Decision

**Transition all law-nexus product and domain functionality to Rust [proposed].**
The existing Python product implementation remains intact as a behavioral
reference until the complete Rust implementation passes all parity, integration,
performance, and failure-surface gates. Then the Python product code moves
wholesale to `python_archive/` in one controlled cutover. A thin Python
repository-control CLI is allowed under ADR-0007; it contains no product logic.

### Migration triggers (when Rust pays off)

The migration is justified when one or more of these conditions materialize:

1. **Corpus growth beyond 10× current size** (≥ 100 in-scope files, ≥ 2 GB raw
   XML). At 7.5 s for 284 MB, Python handles current scale. At 10×, single-
   threaded parse approaches 75 s and memory pressure (DOM XML) becomes real.
2. **Concurrency-bound workloads**: parallel parsing, parallel embedding
   generation, concurrent graph materialization. Python's GIL makes true CPU
   parallelism awkward; Rust's `rayon`/`tokio` make it trivial.
3. **Latency-sensitive retrieval**: once FalkorDB query results need
   sub-100ms post-processing (citation-safe assembly, evidence packing), Rust's
   predictable memory layout wins over Python's allocation/GC behavior.
4. **Memory footprint**: FalkorDB + embedding model + Python runtime can exhaust
   available RAM on a 1 GB corpus. Rust's zero-copy parsing and explicit memory
   management scale linearly.

### Migration non-triggers (when Rust does NOT pay off)

- **Test speed.** M106 proved test architecture was the bottleneck, not Python.
  Rust will not make tests faster if they keep rebuilding artifacts.
- **Single-file correctness.** Parser logic (marker_for_text, hierarchy_records,
  deontic lexemes) is deterministic and already correct in Python. Rewriting it
  in Rust adds risk without fixing bugs.
- **Repository governance tooling.** Tooling language alone is not a migration
  trigger. ADR-0007 permits a thin Python repository-control CLI that launches
  Rust binaries and checks repository contracts without owning product logic.

### Migration strategy

See `doc/adr/0005-rust-target-architecture.md` for the component-by-component
map. **Full product migration to Rust — no PyO3, no in-process bridge, and no
per-component Python deletion [proposed].** Rust is implemented beside the
unchanged Python reference until whole-system parity succeeds. Python product
code is archived only at the final cutover.

Summary:

1. **Phase 1 — freeze behavioral contracts.** Preserve Python outputs, schemas,
   diagnostics, errors, fixtures, performance, and memory baselines as immutable
   Rust parity targets.
2. **Phase 2 — Rust foundation.** Create the Cargo workspace, crate boundaries,
   repository harness, architecture checks, lint/test/security gates, and
   benchmark surfaces. Python product code remains unchanged.
3. **Phase 3 — Rust product implementation.** Implement domain types, parsers,
   adapters, application logic, FalkorDB integration, retrieval, citation-safe
   evidence, observability, and Rust CLIs. Python product code remains unchanged.
4. **Phase 4 — whole-system parity.** Compare Rust against frozen artifacts and
   behavioral contracts across the complete corpus, failures, performance,
   concurrency, memory, graph integration, and UAT.
5. **Phase 5 — one controlled cutover.** Move the entire Python product
   implementation to `python_archive/`, remove it from product CI/runtime, and
   make Rust the sole product runtime. Keep only the ADR-0007 Python repository
   control-plane CLI if it still provides value.

**No PyO3. No in-process bridge. No duplicated product logic in the Python
harness. Rust is the only product runtime after cutover.**

## Consequences

- **Easier — concurrency.** `rayon` for parallel parsing, `tokio` for async I/O,
  no GIL constraints. Enables 10–100× corpus scaling on multi-core.
- **Easier — memory.** Zero-copy XML parsing (`quick-xml`), explicit lifetimes,
  no GC pauses. Predictable memory profile.
- **Easier — deployment.** Single static binary, no `uv`/`pip`/venv, no
  Python version drift. Smaller container image.
- **Harder — velocity (short term).** Rust write-velocity is lower than Python
  for exploratory work. The repository harness reduces operational friction,
  but all product behavior still belongs in Rust.
- **Harder — hiring/contribution.** Smaller contributor pool for Rust legal-tech.
  Accepted as a cost of the full product transition.
- **We will revisit:** whether the ADR-0007 Python repository harness should
  eventually become a Rust CLI. This does not affect the Rust-only product
  runtime boundary.

## Alternatives Considered

### Option A: Stay on Python, optimize hot paths with C extensions / Cython

**Pros:** no rewrite, no new toolchain, lowest risk.
**Cons:** does not solve the concurrency/GIL problem; C extensions are
maintenance-heavy; Cython adds a compile step without the safety benefits of
Rust. Buys time, not a scaling story.

### Option B: Migrate to Go instead of Rust

**Pros:** faster write-velocity than Rust, native concurrency (goroutines),
single static binary, simpler type system.
**Cons:** Go's XML story is weaker than Rust's `quick-xml`; Go's type system is
less expressive for the domain modeling (no sum types until recently, no
traits); Go's garbage collector reintroduces GC pauses. Rust's zero-copy and
explicit memory story is a better fit for legal-text processing at scale.

### Option C: Keep Python product modules behind a PyO3 bridge

**Pros:** incremental call-site migration and short-term compatibility.
**Cons:** permanent bridge maintenance, duplicated product boundaries, GIL and
packaging complexity, and an ambiguous source of product truth. Rejected by
explicit human decision; only process-level repository orchestration is allowed
in Python (ADR-0007).

### Option D: Do nothing until a measured bottleneck appears

**Pros:** zero investment now.
**Cons:** when the bottleneck appears (corpus growth, user-facing latency), the
migration starts from zero under pressure. Preparing the ADRs, target
architecture, and roadmap now (M107) is cheap; doing it under a production
latency incident is expensive.

## References

- **M107-7xtx1c** — this milestone: crystallize requirements/architecture/ADRs
  and write the Rust migration roadmap.
- **D103 / D105 / D106** (`.gsd/DECISIONS.md`) — Rust-only product runtime,
  no in-process bridge, and the narrow Python repository-harness exception.
- **`prd/migration/rust-migration-roadmap.md`** — the phased plan.
- **`prd/migration/rust-target-architecture.md`** — the component-by-component map.
- **`prd/migration/rust-performance-baseline.md`** — the M107 measured baseline.
- **`python_archive/adr/0001-onion-package-structure.md`** — the Python ADR this
  migration supersedes for new code. The onion layering concept survives the
  migration (see ADR-0005).
