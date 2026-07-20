---
id: ADR-0004
title: Rust migration decision for law-nexus
status: Accepted
lifecycle: "[proposed]"
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

**Migrate law-nexus from Python to Rust incrementally, preserving Python until
Rust achieves functional parity per component.**

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
- **ACP/git-lex governance.** The reusable core at `/root/git-lex-kit-acp/` is
  Python and stays Python (governance surface, not product hot path).

### Migration strategy

See `doc/adr/0005-rust-target-architecture.md` for the component-by-component
map and `doc/adr/0006-rust-python-coexistence-strategy.md` for the PyO3
incremental-migration mechanics.

Summary:

1. **Phase 1 — domain types (Rust crate `law-nexus-core`)**. Port the Pydantic
   domain models to Rust structs with serde. No I/O. Parity test: Rust struct
   ↔ Python Pydantic model round-trip JSON equality.
2. **Phase 2 — parsers (hot path)**. Port `consultant_wordml.py` and
   `consultant_hierarchy.py` to Rust using `quick-xml`. Parity test: same XML
   input → byte-identical JSONL output.
3. **Phase 3 — adapters (I/O-bound)**. Port filesystem inventory, graph store,
   embedding client. Parity test: same interface contract.
4. **Phase 4 — application + composition**. Port use cases and wiring. Parity
   test: same CLI output for the same inputs.
5. **Phase 5 — Python removal**. After all phases pass parity, Python moves to
   `python_archive/` and Rust becomes the only runtime.

Each phase has a parity gate. **Python is not removed until the Rust equivalent
passes the same test suite the Python version passes.**

## Consequences

- **Easier — concurrency.** `rayon` for parallel parsing, `tokio` for async I/O,
  no GIL constraints. Enables 10–100× corpus scaling on multi-core.
- **Easier — memory.** Zero-copy XML parsing (`quick-xml`), explicit lifetimes,
  no GC pauses. Predictable memory profile.
- **Easier — deployment.** Single static binary, no `uv`/`pip`/venv, no
  Python version drift. Smaller container image.
- **Harder — velocity (short term).** Rust write-velocity is lower than Python
  for exploratory work. Mitigation: keep Python as the exploration language
  during research milestones; Rust only for validated, stable components.
- **Harder — hiring/contribution.** Smaller contributor pool for Rust legal-tech.
  Mitigation: the PyO3 bridge lets Python-skilled contributors keep working on
  the Python side during migration.
- **We will revisit:** (1) whether Phase 1 (domain types) is worth the cost if
  corpus growth stays under 10× for 12+ months; (2) whether PyO3 is the right
  bridge vs. a hard cutover once Phase 2 (parsers) proves out; (3) whether to
  keep ACP/git-lex in Python permanently (governance surface, low ROI for Rust).

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

### Option C: Migrate to Rust only for the parser, keep the rest in Python

**Pros:** lowest rewrite cost, targets the actual hot path.
**Cons:** two languages in the codebase permanently; two build systems; two test
suites; the "rest" includes graph materialization, retrieval, and citation
assembly, all of which also benefit from Rust. This is Phase 2 of the accepted
plan, not a destination.

### Option D: Do nothing until a measured bottleneck appears

**Pros:** zero investment now.
**Cons:** when the bottleneck appears (corpus growth, user-facing latency), the
migration starts from zero under pressure. Preparing the ADRs, target
architecture, and roadmap now (M107) is cheap; doing it under a production
latency incident is expensive.

## References

- **M107-7xtx1c** — this milestone: crystallize requirements/architecture/ADRs
  and write the Rust migration roadmap.
- **D098** — anti-drift enforcement. This ADR carries lifecycle tags; migration
  progress is tagged `[proposed]` → `[bounded]` → `[validated]` per phase.
- **`prd/migration/rust-migration-roadmap.md`** — the phased plan.
- **`prd/migration/rust-target-architecture.md`** — the component-by-component map.
- **`prd/migration/rust-performance-baseline.md`** — the M107 measured baseline.
- **`python_archive/adr/0001-onion-package-structure.md`** — the Python ADR this
  migration supersedes for new code. The onion layering concept survives the
  migration (see ADR-0005).
