---
id: ADR-0006
title: Rust-Python coexistence strategy (PyO3 incremental migration)
status: Accepted
lifecycle: "[proposed]"
date: 2026-07-18
superseds: none
related: [ADR-0004, ADR-0005, M107-7xtx1c]
---

# ADR-0006: Rust-Python coexistence strategy (PyO3 incremental migration)

## Status

**Accepted [proposed]** — strategy documented. No PyO3 bindings exist yet.
Moves to `[bounded]` when the first Rust crate is callable from Python via
`law-nexus-py`, and to `[validated]` when the Python test suite passes against
Rust-backed implementations.

## Context

ADR-0004 decides to migrate incrementally. ADR-0005 defines the Rust target.
This ADR answers: **how do Python and Rust coexist during the 4-phase migration
without breaking the existing test suite or forcing a big-bang cutover?**

The constraint is severe: law-nexus has 2079 passing Python tests and 94
fixtures that encode legal-domain expectations. A migration that breaks those
tests mid-flight is a migration that will be reverted. The coexistence strategy
must let Rust and Python run the same test suite, with Rust implementations
slotting in component-by-component.

## Decision

**Use PyO3 [proposed]** to expose Rust crates as a Python importable module
(`law_nexus_rust`), and replace Python implementations one component at a time
behind the existing Python API.**

### The bridge: `law-nexus-py` crate

A dedicated crate (`law-nexus-py/`, part of the Cargo workspace) wraps Rust
crates with `#[pyfunction]` and `#[pymodule]` attributes. Python imports it as
`law_nexus_rust`:

```python
# After Phase 1 (domain types):
from law_nexus_rust.domain import SourceDocument  # Rust-backed
# replaces: from law_nexus.domain.source_document import SourceDocument
```

The bridge handles:

1. **Type conversion.** Pydantic `BaseModel` ↔ Rust serde struct via JSON string
   round-trip (simple, verifiable, slow enough to catch in benchmarks). Later
   optimization: direct field mapping via `pyclass` if JSON round-trip shows up
   in profiles.
2. **Error bridging.** Rust `Result<T, E>` → Python exception. `pyo3::PyValueError`
   for validation, custom exceptions for domain errors.
3. **GIL awareness.** Rust functions that do not touch Python release the GIL
   (`Python::with_gil` only at the boundary). Parser hot paths run GIL-free.

### Migration mechanics per phase

| Phase | Rust crate | Python call site | Parity gate |
|---|---|---|---|
| 1 (domain) | `law-nexus-core` | `law_nexus_rust.domain.SourceDocument` | Python test suite passes with Rust-backed domain types. JSON round-trip equality on 94 fixtures. |
| 2 (parsers) | `law-nexus-parser` | `law_nexus_rust.parser.consultant_hierarchy_records(...)` | `scripts/build-consultant-hierarchy-records.py` delegates to Rust; byte-identical JSONL output on 94-fixture corpus. |
| 3 (adapters) | `law-nexus-adapters` | `law_nexus_rust.adapters.filesystem_inventory(...)` | `scripts/build-parser-staging-graph.py` delegates to Rust; same staging graph JSON. |
| 4 (application) | `law-nexus-app` | CLI entry points call Rust directly via PyO3 | `pytest -m "not slow"` passes; full corpus run byte-identical. |
| 5 (removal) | — | Python deleted; `law_nexus_rust` renamed or inlined | Python test suite ported to Rust tests; Python removed from CI. |

### Delegation pattern

During Phases 1–4, each Python module that has a Rust equivalent uses a
delegation pattern:

```python
# src/law_nexus/adapters/sources/consultant_hierarchy.py (during Phase 2)
try:
    from law_nexus_rust.parser import consultant_hierarchy_records as _rust_impl
    _USE_RUST = True
except ImportError:
    _USE_RUST = False

def consultant_hierarchy_records(xml_path, **kwargs):
    if _USE_RUST:
        return _rust_impl(str(xml_path), **kwargs)
    # ... existing Python implementation ...
```

This lets the Rust implementation be absent (during development) without
breaking the test suite, and present (after parity) without changing call sites.

### Parity testing

A dedicated test module `tests/parity/` runs the same inputs through both the
Python and Rust implementations and asserts equality:

```python
# tests/parity/test_consultant_hierarchy.py
def test_parity_consultant_hierarchy_on_44fz():
    py_result = python_impl(...)
    rs_result = rust_impl(...)
    assert py_result == rs_result  # structural equality
```

Parity tests gate phase progression. **A phase does not advance until parity
tests pass on the full 94-fixture corpus.**

### Build and CI

- **Cargo workspace** at repo root builds all Rust crates.
- **Maturin** builds the `law-nexus-py` wheel: `maturin develop` for local dev,
  `maturin build --release` for CI.
- **CI matrix** runs both `uv run pytest` (Python, with Rust delegation if
  available) and `cargo test` (Rust unit/integration).
- **Pre-commit** runs `cargo fmt --check` and `cargo clippy` alongside existing
  Python hooks.

### What does NOT cross the bridge

- **ACP/git-lex reusable core.** Stays pure Python (ADR-0004 non-trigger). Rust
  does not import it; Python continues to.
- **`.gsd/` tooling.** Stays Node.js/TypeScript.
- **Research scripts.** Stays Python (exploratory).

## Consequences

- **Easier — incremental, low-risk migration.** Each phase ships behind the
  existing Python API. Rollback is "delete the `law_nexus_rust` import." No
  big-bang cutover.
- **Easier — continuous parity verification.** The delegation pattern forces
  Rust and Python to stay in sync. Drift is caught immediately.
- **Easier — gradual team migration.** Python-skilled contributors keep working
  on the Python side; Rust-skilled contributors port components in parallel.
- **Harder — bridge maintenance overhead.** Type conversion, error mapping, and
  GIL management add code that exists only during migration. Mitigation: Phase 5
  removes the bridge once Rust is the only runtime.
- **Harder — build complexity.** Two build systems (Cargo + uv) during
  migration. CI time increases. Mitigation: cache Cargo builds aggressively;
  skip Rust build on Python-only PRs.
- **We will revisit:** (1) whether JSON round-trip type conversion is fast
  enough or if we need `pyclass` direct mapping early; (2) whether to keep
  `law-nexus-py` after Phase 5 as a Python interop surface for the ACP/git-lex
  side; (3) whether to publish `law-nexus-core` as a library crate consumable
  by the ACP/git-lex Python side via PyO3 (reversing the dependency direction).

## Alternatives Considered

### Option A: Big-bang cutover (rewrite everything, switch when done)

**Pros:** no bridge maintenance; clean Rust-only codebase at the end.
**Cons:** months of parallel development with no user-visible progress; high
risk of the rewrite never finishing; loses the 2079-test safety net during the
transition. Unacceptable for a project with active milestones.

### Option B: Side-by-side Rust binary, no Python bridge

**Pros:** Rust is a separate CLI; Python stays untouched.
**Cons:** no shared test suite; parity is manual; drift goes unnoticed; the
"separate CLI" tends to become the abandoned one. Rejected.

### Option C: PyO3 with direct `pyclass` types (no JSON round-trip)

**Pros:** faster type conversion than JSON round-trip.
**Cons:** requires defining every type as `#[pyclass]` from day one, coupling
Rust domain types to Python object model before the domain is stable. JSON
round-trip is the simplest verifiable bridge; upgrade to `pyclass` later if
profiles demand it.

## References

- **ADR-0004** — the migration decision.
- **ADR-0005** — the Rust target architecture.
- **PyO3** (`https://pyo3.rs`) — Rust-Python bindings.
- **Maturin** (`https://www.maturin.rs`) — PyO3 build tool.
- **M107-7xtx1c** — this milestone (coexistence strategy documentation).
