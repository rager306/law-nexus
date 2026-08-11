---
id: ADR-0005
title: Rust target architecture for law-nexus
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-18
supersedes: none
superseded_by: [ADR-0011#crate-map-only] # narrow D127 supersession; archived Python ADR is prior art
related: [ADR-0004, ADR-0007, ADR-0011, ADR-0013, ADR-0014, D123, D127]
---

# ADR-0005: Rust target architecture for law-nexus

## Status

**Accepted [bounded].** The onion layering direction is realized in the Rust
product runtime, but the **crate map below is superseded by ADR-0011 (D127)** —
the actual workspace is twenty exclusive `ln-*` capability-owner crates, not the
four-crate `law-nexus-core/parser/adapters/app` sketch in this ADR. ADR-0013
supersedes the parser crate section with the `ln-decode` universal parser.
Read the crate map below as historical planning, superseded by ADR-0011/0013.
The onion/hexagonal layering principle (domain → ports → application → adapters)
survives intact and is enforced in the real `ln-*` workspace.

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

> **⚠️ SUPERSEDED by ADR-0011 (D127) and ADR-0013.** The four-crate sketch below
> was pre-implementation planning. The real workspace is twenty exclusive `ln-*`
capability-owner crates (ADR-0011 KOF-DA ownership) plus `ln-decode` universal
parser (ADR-0013). It is retained as historical context for the onion intent.

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
```

A workspace `Cargo.toml` at the repo root ties the crates together. **No PyO3
crate or in-process Python binding [proposed].** A separate Python repository
harness may invoke Rust binaries across process boundaries only (ADR-0007).

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

### What does NOT become Rust product code

- **ACP/git-lex surfaces.** They are decommissioned from active law-nexus per
  D104 and archived separately; they are not ported to Rust.
- **`.gsd/` tooling.** It remains external repository workflow infrastructure.
- **Python repository harness (ADR-0007).** It may orchestrate Rust binaries,
  Cargo checks, architecture/ADR conformance, document freshness, parity
  artifacts, CI, and GSD. It must not implement product or domain behavior.
- **Historical and research documents.** They are evidence/history, not runtime
  implementation targets.

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
- **Harder — parity verification.** Rust tests are per-crate while complete
  parity spans artifacts and binaries. ADR-0007's Python harness orchestrates
  process-level comparisons against frozen Python-generated JSONL/JSON fixtures;
  it never imports or calls Rust in-process.
- **We will revisit:** (1) whether to use `axum`/`actix` for a future HTTP API
  surface (deferred until retrieval is productized); (2) whether to split
  `law-nexus-parser` into per-format crates (`law-nexus-consultant`,
  `law-nexus-garant`) once Garant is in scope; (3) whether the repository
  harness eventually moves from Python to Rust.

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

## Non-claims

- The four-crate sketch in this ADR is **not** the current workspace map (superseded by ADR-0011 / D127).
- No claim that every Python module has a one-to-one Rust crate today.
- Parser completeness and legal correctness are not claimed (see ADR-0013).

## References

- **ADR-0004** — the migration decision this architecture serves.
- **`python_archive/adr/0001-onion-package-structure.md`** — the Python onion
  ADR. Its layering concept survives; its Python-specific decisions (Pydantic,
  import-linter, factory functions) are replaced by Rust idioms.
- **`prd/migration/rust-target-architecture.md`** — the detailed per-component
  migration plan with phase boundaries.
- **`src/law_nexus/`** — the current Python behavioral reference. It remains
  intact until whole-system Rust parity and then moves wholesale to
  `python_archive/`.
