# law-nexus Product Architecture Matrix and Forward Roadmap

**Status:** `[proposed]`
**Date:** 2026-07-24
**Author:** pi session after M129 (20/0/0 hostile case aggregate)

## Current State

All 20 hostile cases have bounded Rust runtime PASS. These prove adversarial
contracts (dual-writer rejection, fail-closed, non-authority enforcement) in
synthetic hexagonal seams. They do NOT prove real product behavior.

### What exists

- **41 Rust crates** (20 domain + 20 runners + 1 status tracer)
- **Python product reference** (parser, hierarchy, retrieval, citation, staging)
- **Python harness** (governor, preflight, subprocess runner, architecture/ADR checks)
- **Frozen baselines** (corpus manifest, golden cases, ADR registry)

### What does NOT exist

- Real Rust parser for Consultant XML or Garant ODT
- Rust FalkorDB client or graph materialization
- Rust embedding/vector/retrieval pipeline
- Rust citation-safe answer assembly
- Rust product CLI beyond status/hc-runners
- ruVector integration
- Whole-system parity testing
- Any product capability validated as `[validated]`

## Matrix: Module → Deficiency → Feature → Milestone → Dependency

### Layer 1: Domain Types (R3)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Source/Document/Edition ID | ln-observe | Synthetic only; no real Rust types matching Python domain | Rust SourceDocument, ActEdition, SourceBlock, EvidenceSpan, NormStatement, LegalUnit, Citation types with serde/schemars | None | R0 baseline (done) |
| Hierarchy types | ln-observe | No Rust RawBlock/level/parent | Rust hierarchy types matching frozen manifest | None | Source types |
| Temporal types | ln-temporal | Synthetic clock only | Rust ActVersion, EffectiveDate, TimeBoundary | None | Source types |
| Authority types | ln-publish | Synthetic PublicationAuthority | Rust AuthoritySurface, PublicationRecord matching D120 | None | Source types |

### Layer 2: Parser (R4)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Consultant XML parser | ln-decode | Synthetic decoder only | Real `quick-xml` streaming parser for Consultant XML: hierarchy, FRBR IDs, references, temporal markers, deontic lexemes | None | R3 domain types |
| Garant ODT parser | ln-decode | Not started | ODT XML parser for Garant source documents | None | R3, Consultant parser |
| Parser pipeline | ln-decode | No artifact builder | Hierarchy/relation/norm builders, staging graph builder, golden evaluator | None | Both parsers |

### Layer 3: Graph (R5-R6)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| FalkorDB Rust client | None | Does not exist | Verified Rust client for FalkorDB with parameterized queries, timeouts, error taxonomy | ruVector could provide graph/vector bridge (separate-role) | R3-R5 |
| Graph materialization | ln-relation, ln-projection | Synthetic only | Real graph ingest: idempotent MERGE, relation/reference edges, cleanup | None | FalkorDB client |
| Generated Cypher safety | ln-query | Synthetic only | Deterministic Cypher validation before execution; parameter binding; injection rejection | None | FalkorDB client |

### Layer 4: Retrieval and Citation (R7)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Embedding adapter | None | Does not exist | Local/open-weight embedding model adapter (USER-bge-m3 or equivalent) in Rust | ruVector can provide vector store/compute (separate-role, ADR-0012) | R3 domain types |
| Exact retrieval | ln-query | Synthetic only | Article/clause exact match retrieval from materialized graph | None | FalkorDB graph |
| Vector retrieval | None | Does not exist | Vector similarity search over EvidenceSpan embeddings | ruVector vector store integration candidate; FalkorDB vector index alternative | Embedding adapter |
| Graph-filtered retrieval | ln-query, ln-relation | Synthetic only | Temporal + authority + relation graph traversal for filtered retrieval | None | Exact + vector retrieval |
| Citation assembly | ln-citation | Synthetic only | EvidenceSpan→Citation binding with source-authority check; missing-anchor fail-closed | None | Graph-filtered retrieval |
| Output validator | ln-diagnostic | Synthetic only | No-answer/candidate-only output validation; reason codes; safe diagnostic emission | ruVector diagnostic sink candidate (ADR-0012 separate-role) | Citation assembly |

### Layer 5: Application and CLI (R8)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Ingest use case | ln-observe, ln-inventory | Synthetic only | Real ingest: parse → profile → build → load → verify pipeline | None | R4-R7 |
| Composition root | None | Does not exist | Rust composition root wiring all adapters | None | All use cases |
| Product CLI | ln-status | Tracer only | Stable CLI: ingest, profile, build, load, retrieve, verify, status | None | Composition root |
| Job/state management | ln-work, ln-replay | Synthetic only | Phase/failure persistence, timeouts, cleanup, resource budgets | None | Product CLI |

### Layer 6: Conformance and Parity (R9)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Whole-system parity | ln-conformance | Oracle only | Schema/determinism/failure parity vs frozen Python artifacts | None | R3-R8 complete |
| Conformance meta-suite | ln-conformance | Honest oracle only | Real HC-01 through HC-20 verdicts from Rust product runtime | None | Whole-system parity |
| Performance benchmarks | None | Does not exist | 1×/10× corpus benchmarks; memory profile; concurrency | ruVector performance potential for vector compute | Product CLI |
| Security audit | None | Does not exist | Dependency/license/vulnerability audit | None | Product CLI |

### Layer 7: Python Cutover (R10)

| Module | Deficiency | Feature needed | Depends |
|--------|------------|----------------|---------|
| Python archival | Python product still active | Move all `src/law_nexus/` to `python_archive/product/`; keep `src/law_nexus_harness/` | R9 PASS |
| Docs rewrite | Docs reference Python product | Update README, ARCHITECTURE, ADR, requirements for Rust-only | Python archival |

## ruVector Integration Points

Per ADR-0012, ruVector is `separate-role`: agent runtime, memory, adaptive
retrieval, and optional graph/vector computation. It is never ledger or legal
authority. Integration candidates:

| Integration point | Phase | Role | Boundary |
|-------------------|-------|------|----------|
| Vector store for EvidenceSpan embeddings | R7 | Replace or augment FalkorDB vector index | Separate-role; law-nexus owns citation authority, not ruVector |
| Adaptive retrieval ranking | R7 | Boost/penalize retrieval candidates based on agent feedback | Non-authoritative; output validator must remain fail-closed |
| Diagnostic aggregation | R7-R8 | Aggregate and redact diagnostic signals across pipeline phases | Must route through ln-diagnostic safe emission; raw legal text forbidden |
| Agent memory for session context | R8+ | Store agent conversation/retrieval context across sessions | Separate-role; never product ledger or legal authority |
| Graph/vector computation acceleration | R7 | Batch vector similarity for large corpus retrieval | Performance optimization; correctness must be verifiable without ruVector |

**Key constraint:** ruVector may never become a hard dependency for product
correctness. If ruVector is unavailable, law-nexus must fall back to FalkorDB
vector index or exact retrieval. The output validator and citation assembly
must work identically with or without ruVector.

## Deficiency Priority (Клей — Fix Order)

Deficiencies must be fixed in dependency order. Each layer depends on the
previous one:

```text
R3 Domain Types
  └─ R4 Parser (Consultant XML → Garant ODT → Pipeline)
       └─ R5 Parser Artifacts (Golden pipeline, staging graph)
            └─ R6 FalkorDB Graph (Client → Ingest → Cypher safety)
                 └─ R7 Retrieval (Embedding → Exact → Vector → Graph-filtered → Citation → Validator)
                      │    ruVector integration candidate (vector store, adaptive ranking)
                      └─ R8 Application (Ingest → Composition → CLI → Jobs)
                           └─ R9 Parity (Whole-system → Performance → Security)
                                └─ R10 Python Cutover
```

## Forward Roadmap: Milestones M130+

| Milestone | Phase | Title | Slices | Risk | Key Output |
|-----------|-------|-------|--------|------|------------|
| M130 | R3 | Rust Domain and Serialization Contracts | 6 thin slices by aggregate | high | Rust domain types with serde, schemars, property tests, parity fixtures |
| M131 | R4.1-R4.3 | Consultant XML Parser Foundation | 3 slices: metadata/blocks, hierarchy, parentage | critical | Real XML fixture → Rust hierarchy records matching frozen baseline |
| M132 | R4.4-R4.6 | Consultant XML Parser Advanced | 3 slices: zones, FRBR IDs, references | critical | Full Consultant XML pipeline for single-fixture parity |
| M133 | R4.7-R4.10 | Consultant XML Parser Completion | 4 slices: temporal, deontic, staging, parallel corpus | critical | Full corpus deterministic build matching Python artifacts |
| M134 | R4/R5 | Garant ODT Parser | 3 slices: ODT structure, hierarchy, content | high | Garant ODT → Rust records matching Python |
| M135 | R5 | Parser Golden Pipeline | 4 slices: validation, builders, staging graph, golden evaluator | high | All parser artifacts match frozen contract |
| M136 | R6.1-R6.3 | FalkorDB Rust Client | 3 slices: client verify, graph access, error taxonomy | high | Verified FalkorDB Rust client with integration tests |
| M137 | R6.4-R6.6 | Graph Materialization and Cypher Safety | 3 slices: ingest, edges, Cypher validation | high | Real graph ingest from parsed data |
| M138 | R7.1-R7.2 | Embedding and Exact Retrieval | 2 slices: embedding adapter, exact retrieval | high | Local embedding + article-level exact search |
| M139 | R7.3-R7.4 | Vector and Graph-Filtered Retrieval | 2 slices: vector search, graph-filtered | high | Hybrid retrieval with temporal/authority filters |
| M140 | R7.5-R7.7 | Citation Assembly and Output Validation | 3 slices: citation binding, output validator, fail-closed no-answer | high | Citation-safe answer assembly with golden cases |
| M141 | R8 | Application Composition and Product CLI | 4 slices: ingest use case, composition root, CLI, job management | medium | Full product CLI: ingest→retrieve→verify |
| M142 | R9 | Whole-System Parity and Scale | 5 parallel verification classes | critical | Parity PASS against frozen Python artifacts |
| M143 | R10 | Python Product Archival Cutover | 1 controlled operation | critical | Python product moved to python_archive/; Rust-only active |

**Total estimated milestones:** 14 (M130-M143)
**Total estimated slices:** ~45
**Critical path:** R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10

## ruVector Optimization Milestone (Optional, Parallel)

| Milestone | Phase | Title | Depends | Risk |
|-----------|-------|-------|---------|------|
| M-RV | R7+ | ruVector Integration Pilot | M139 (vector retrieval) | medium |

Slices:
1. ruVector vector store adapter for EvidenceSpan embeddings
2. Adaptive retrieval ranking with agent feedback (non-authoritative)
3. Performance benchmark: ruVector vs FalkorDB vector index
4. Fallback verification: law-nexus works identically without ruVector

**Key decision point:** After M-RV S03, decide whether ruVector becomes the
primary vector backend or stays as an optional acceleration layer.

## Non-Claims

- This matrix is `[proposed]` planning. No product capability is claimed.
- ruVector integration is exploratory; ADR-0012 `separate-role` disposition
  holds until a bounded proof packet changes it.
- All 20 hostile case crates are `[bounded]` synthetic proof, not product
  validation.
- Migration phases R3-R10 follow the frozen roadmap in
  `prd/migration/rust-migration-roadmap.md`.
