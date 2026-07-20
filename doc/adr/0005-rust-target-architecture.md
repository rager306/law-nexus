---
id: ADR-0005
title: Rust target architecture for law-nexus
status: Accepted
lifecycle: "[proposed]"
date: 2026-07-18
superseds: python_archive/adr/0001-onion-package-structure.md (for new code)
related: [ADR-0004, M107-7xtx1c]
---

# ADR-0005: Rust target architecture for law-nexus

## Status

**Accepted [proposed]** — target architecture documented. No Rust code exists
yet. Moves to `[bounded]` when `law-nexus-core` crate (domain types) ships with
parity tests, and to `[validated]` when the full onion is ported.

## Context

ADR-0004 records the Rust migration decision. This ADR answers: **what does the
Rust codebase look like, and how does each Python component map to it?**

The Python codebase (M106 state) is a four-layer onion package
(`src/law_nexus/`):

```
src/law_nexus/
├── domain/          # Pydantic v2 models (SourceDocument, SourceBlock, ...)
├── ports/           # typing.Protocol contracts (Parser, GraphStore, ...)
├── application/     # use cases (Ingest)
├── adapters/        # infrastructure (parsers, sources, graph, retrieval)
└── composition.py   # factory root
```

The onion layering **survives the migration**. What changes is the
implementation language and the idioms within each layer.

## Decision

### Crate structure

```
law-nexus-core/     # Phase 1: domain types + ports (no I/O)
├── src/
│   ├── domain/     # structs: SourceDocument, SourceBlock, NormStatement, ...
│   └── ports/      # trait definitions: Parser, GraphStore, Embedder, LLMClient
└── Cargo.toml

law-nexus-parser/   # Phase 2: parsers (hot path)
├── src/
│   ├── consultant_wordml.rs   # Consultant XML/WordML parser
│   ├── consultant_hierarchy.rs # hierarchy extraction, markers, FRBR ids
│   └── garant_odt.rs          # Garant ODT parser (future)
└── Cargo.toml

law-nexus-adapters/ # Phase 3: I/O-bound adapters
├── src/
│   ├── filesystem_inventory.rs # replace scripts/filesystem_inventory.py
│   ├── falkordb.rs             # replace adapters/graph/
│   ├── embeddings.rs           # replace adapters/embeddings/
│   └── retrieval.rs            # replace adapters/retrieval/
└── Cargo.toml

law-nexus-app/      # Phase 4: use cases + composition
├── src/
│   ├── application/  # use cases (Ingest, Retrieve)
│   ├── composition.rs # factory root
│   └── bin/           # CLI entry points (replace scripts/build-*.py)
└── Cargo.toml

law-nexus-py/       # Phase 1-4 bridge: PyO3 bindings (see ADR-0006)
├── src/
│   └── lib.rs        # #[pyfunction] wrappers around Rust crates
└── Cargo.toml
```

A workspace `Cargo.toml` at the repo root ties the crates together.

### Component-by-component port map

| Python component | Rust target | Migration path | Parity test |
|---|---|---|---|
| `domain/source_document.py` (Pydantic) | `law-nexus-core/src/domain/source_document.rs` (serde struct) | Direct struct translation. Pydantic validators → `#[serde(deserialize_with = ...)]`. | JSON round-trip equality. |
| `domain/source_block.py` | `.../source_block.rs` | Same as above. | Same. |
| `domain/norm_statement.py` | `.../norm_statement.rs` | Same; deontic enum → Rust enum. | Same. |
| `ports/source_hierarchy.py` (Protocol) | `.../ports/source_hierarchy.rs` (trait) | `typing.Protocol` → `trait`. `@runtime_checkable` → `impl Trait` bounds. | Trait object compiles. |
| `adapters/parsers/consultant_wordml.py` | `law-nexus-parser/src/consultant_wordml.rs` | `xml.etree.ElementTree` → `quick-xml` (streaming). | Byte-identical JSONL output on 94-fixture corpus. |
| `adapters/sources/consultant_hierarchy.py` | `law-nexus-parser/src/consultant_hierarchy.rs` | `marker_for_text`, `hierarchy_records`, `extract_internal_references`, `detect_temporal_markers`, `detect_deontic_lexemes` → Rust functions. | Same JSONL output, same diagnostic counters. |
| `adapters/sources/filesystem_inventory.py` | `law-nexus-adapters/src/filesystem_inventory.rs` | `ET.parse` → `quick-xml::Reader`. DOM → streaming. | Same inventory JSON. |
| `scripts/build-consultant-hierarchy-records.py` | `law-nexus-app/src/bin/build_consultant_hierarchy_records.rs` | `subprocess.run` → direct function call. `argparse` → `clap`. | Same CLI output for `--corpus` and `--check`. |
| `scripts/build-consultant-relation-candidates.py` | `.../build_consultant_relation_candidates.rs` | Same pattern. | Same relation candidates JSONL. |
| `scripts/build-consultant-norm-candidates.py` | `.../build_consultant_norm_candidates.rs` | Same pattern. | Same norm candidates JSONL. |
| `scripts/build-parser-staging-graph.py` | `.../build_parser_staging_graph.rs` | Same pattern. | Same staging graph JSON. |

### Idiom translations

| Python | Rust | Notes |
|---|---|---|
| `pydantic.BaseModel` | `serde::Serialize` struct with `#[derive(Deserialize)]` | Validation via `#[serde(...)]` attributes or custom visitors. |
| `typing.Protocol` | `trait` | Rust traits are explicit; no `runtime_checkable` needed. |
| `@dataclass` | `#[derive(Debug, Clone)] struct` | No mutable default sharing (Python footgun avoided). |
| `enum.Enum` | Rust `enum` (sum types) | Rust enums are real sum types; better for deontic categories. |
| `xml.etree.ElementTree` (DOM) | `quick-xml::Reader` (streaming) | Zero-copy; lower memory; faster on large XML. |
| `pathlib.Path` | `std::path::PathBuf` | Direct translation. |
| `subprocess.run([sys.executable, ...])` | direct function call | No process spawn; no interpreter startup. |
| `pytest` fixtures | Rust test modules + `#[test]` | No session-scoped fixture needed; tests are cheap. |
| `argparse` | `clap` (derive) | Declarative CLI with strong types. |
| `uv run python` | `cargo run` | No virtualenv; no `uv`. |
| `import-linter` onion contract | Rust module visibility (`pub(crate)`, `pub(super)`) | Compiler-enforced layering, not tooling-enforced. |

### What does NOT migrate

- **ACP/git-lex reusable core** (`/root/git-lex-kit-acp/`). Stays Python. It is
  a governance/recovery surface, not a product hot path. See ADR-0004
  "non-triggers."
- **`.gsd/` tooling.** Stays whatever GSD ships (Node.js/TypeScript).
- **`.lex/` extract state.** Stays as-is (ACP projection, not product).
- **Research scripts** (`prd/research/`). Exploratory Python is fine; Rust is
  for validated, stable components only.

## Consequences

- **Easier — compiler-enforced layering.** Module visibility replaces
  import-linter. The onion boundaries become compile errors, not CI warnings.
- **Easier — zero-copy XML.** `quick-xml` streams 284 MB without building a DOM.
  Memory footprint drops by ~5–10×.
- **Easier — real sum types.** Deontic categories (obligation/permission/
  prohibition) become a Rust `enum` with exhaustive matching. No more
  stringly-typed bugs.
- **Harder — Pydantic ecosystem loss.** JSON Schema generation, validation
  error messages, `TypeAdapter` — all need Rust equivalents (`schemars`,
  custom validators). Mitigation: Phase 1 is domain types only; learn the
  serde/schemars stack before tackling parsers.
- **Harder — incremental testing.** Rust's test story is per-crate, not
  session-scoped fixtures. Parity tests need a Python-in-Docker sidecar during
  migration. Mitigation: `law-nexus-py` crate (ADR-0006) provides the bridge.
- **We will revisit:** (1) whether to use `axum`/`actix` for a future HTTP API
  surface (deferred until retrieval is productized); (2) whether `law-nexus-core`
  should be published to a private registry for the ACP/git-lex side to consume
  (deferred); (3) whether to split `law-nexus-parser` into per-format crates
  (`law-nexus-consultant`, `law-nexus-garant`) once Garant is in scope.

## Alternatives Considered

### Option A: Single crate, module-based layering

**Pros:** simplest workspace; no cross-crate visibility games.
**Cons:** loses the "domain has no I/O" guarantee at the crate level. With one
crate, a parser module can `use crate::domain::*` and a domain module can
accidentally `use crate::parser::*`. Multi-crate makes the boundary physical.

### Option B: Workspace with `law-nexus` as the only crate, features for layers

**Pros:** feature flags let you compile "core only" vs "full app."
**Cons:** feature flags are a maintenance trap; conditional compilation hides
breaking changes. Multi-crate with a workspace is cleaner and what the Rust
ecosystem recommends.

### Option C: Monorepo with separate Rust and Python directories, no shared workspace

**Pros:** clear language boundary.
**Cons:** loses the Cargo workspace benefits (shared `Cargo.lock`, single
`cargo test` run, cross-crate refactoring). The accepted plan keeps the Rust
crates in one workspace.

## References

- **ADR-0004** — the migration decision this architecture serves.
- **ADR-0006** — the PyO3 coexistence strategy for incremental migration.
- **`python_archive/adr/0001-onion-package-structure.md`** — the Python onion
  ADR. Its layering concept survives; its Python-specific decisions (Pydantic,
  import-linter, factory functions) are replaced by Rust idioms.
- **`prd/migration/rust-target-architecture.md`** — the detailed per-component
  migration plan with phase boundaries.
- **`src/law_nexus/`** — the current Python package being ported.
